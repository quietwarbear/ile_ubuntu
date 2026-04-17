"""Quiz routes — full quiz builder with multiple question types and grading."""

from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import uuid
from database import quizzes_col, quiz_attempts_col, lessons_col, courses_col, enrollments_col
from middleware import get_current_user
from models.user import has_permission, UserRole

router = APIRouter(prefix="/api/courses/{course_id}/lessons/{lesson_id}/quiz", tags=["quizzes"])

# Question types
QUESTION_TYPES = {"multiple_choice", "true_false", "short_answer", "matching"}


def _check_course_instructor(course_id: str, current_user: dict):
    """Verify the user is the course instructor or an admin/assistant."""
    course = courses_col.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["instructor_id"] != current_user["id"] and not has_permission(current_user["role"], UserRole.ASSISTANT):
        raise HTTPException(status_code=403, detail="Access denied")
    return course


def _get_lesson(course_id: str, lesson_id: str):
    lesson = lessons_col.find_one({"id": lesson_id, "course_id": course_id})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


def _auto_grade(quiz: dict, answers: dict) -> dict:
    """Auto-grade objective questions. Returns scores and feedback per question."""
    questions = quiz.get("questions", [])
    results = []
    total_points = 0
    earned_points = 0
    needs_manual_review = False

    for q in questions:
        qid = q["id"]
        q_type = q["type"]
        max_pts = q.get("points", 1)
        total_points += max_pts
        user_answer = answers.get(qid, "")

        result = {
            "question_id": qid,
            "user_answer": user_answer,
            "correct_answer": q.get("correct_answer"),
            "points_possible": max_pts,
            "points_earned": 0,
            "is_correct": None,
            "needs_review": False,
        }

        if q_type == "multiple_choice":
            is_correct = str(user_answer).strip().lower() == str(q["correct_answer"]).strip().lower()
            result["is_correct"] = is_correct
            result["points_earned"] = max_pts if is_correct else 0
            earned_points += result["points_earned"]

        elif q_type == "true_false":
            is_correct = str(user_answer).strip().lower() == str(q["correct_answer"]).strip().lower()
            result["is_correct"] = is_correct
            result["points_earned"] = max_pts if is_correct else 0
            earned_points += result["points_earned"]

        elif q_type == "matching":
            # answers is a dict of {left_item: right_item}
            correct_pairs = q.get("correct_answer", {})
            if isinstance(user_answer, dict) and isinstance(correct_pairs, dict):
                correct_count = sum(
                    1 for k, v in user_answer.items()
                    if correct_pairs.get(k, "").strip().lower() == str(v).strip().lower()
                )
                total_pairs = len(correct_pairs)
                pts = round((correct_count / total_pairs) * max_pts, 1) if total_pairs > 0 else 0
                result["points_earned"] = pts
                result["is_correct"] = correct_count == total_pairs
                earned_points += pts
            else:
                result["points_earned"] = 0
                result["is_correct"] = False

        elif q_type == "short_answer":
            # Short answer needs manual review by facilitator
            result["needs_review"] = True
            needs_manual_review = True

        results.append(result)

    score_pct = round((earned_points / total_points) * 100, 1) if total_points > 0 else 0

    return {
        "results": results,
        "total_points": total_points,
        "earned_points": earned_points,
        "score_percentage": score_pct,
        "needs_manual_review": needs_manual_review,
    }


# ---------------------------------------------------------------------------
# Quiz CRUD (instructor/facilitator)
# ---------------------------------------------------------------------------

@router.post("")
async def create_quiz(course_id: str, lesson_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Create a quiz for a lesson."""
    _check_course_instructor(course_id, current_user)
    _get_lesson(course_id, lesson_id)

    # Only one quiz per lesson
    existing = quizzes_col.find_one({"lesson_id": lesson_id})
    if existing:
        raise HTTPException(status_code=400, detail="This lesson already has a quiz. Update or delete it first.")

    data = await request.json()
    questions = data.get("questions", [])

    # Validate questions
    for i, q in enumerate(questions):
        if q.get("type") not in QUESTION_TYPES:
            raise HTTPException(status_code=400, detail=f"Question {i+1}: invalid type '{q.get('type')}'")
        if not q.get("text"):
            raise HTTPException(status_code=400, detail=f"Question {i+1}: text is required")
        q["id"] = q.get("id") or str(uuid.uuid4())
        q["points"] = q.get("points", 1)

    quiz = {
        "id": str(uuid.uuid4()),
        "course_id": course_id,
        "lesson_id": lesson_id,
        "title": data.get("title", "Lesson Quiz"),
        "description": data.get("description", ""),
        "questions": questions,
        "pass_threshold": data.get("pass_threshold", 70),
        "max_attempts": data.get("max_attempts", 3),
        "show_correct_answers": data.get("show_correct_answers", True),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    quizzes_col.insert_one(quiz)
    quiz.pop("_id", None)

    # Mark lesson as having a quiz
    lessons_col.update_one({"id": lesson_id}, {"$set": {"has_quiz": True}})

    return quiz


@router.get("")
async def get_quiz(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Get the quiz for a lesson. Students don't see correct answers."""
    _get_lesson(course_id, lesson_id)
    quiz = quizzes_col.find_one({"lesson_id": lesson_id}, {"_id": 0})
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")

    # Hide correct answers from students
    is_instructor = has_permission(current_user["role"], UserRole.FACULTY)
    if not is_instructor:
        for q in quiz.get("questions", []):
            q.pop("correct_answer", None)
            q.pop("explanation", None)

    return quiz


@router.put("")
async def update_quiz(course_id: str, lesson_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Update the quiz for a lesson."""
    _check_course_instructor(course_id, current_user)
    quiz = quizzes_col.find_one({"lesson_id": lesson_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")

    data = await request.json()
    update_fields = {}
    for field in ["title", "description", "questions", "pass_threshold", "max_attempts", "show_correct_answers"]:
        if field in data:
            update_fields[field] = data[field]

    if "questions" in update_fields:
        for i, q in enumerate(update_fields["questions"]):
            if q.get("type") not in QUESTION_TYPES:
                raise HTTPException(status_code=400, detail=f"Question {i+1}: invalid type")
            q["id"] = q.get("id") or str(uuid.uuid4())
            q["points"] = q.get("points", 1)

    update_fields["updated_at"] = datetime.now(timezone.utc)
    quizzes_col.update_one({"lesson_id": lesson_id}, {"$set": update_fields})
    updated = quizzes_col.find_one({"lesson_id": lesson_id}, {"_id": 0})
    return updated


@router.delete("")
async def delete_quiz(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Delete the quiz for a lesson."""
    _check_course_instructor(course_id, current_user)
    result = quizzes_col.delete_one({"lesson_id": lesson_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")
    lessons_col.update_one({"id": lesson_id}, {"$set": {"has_quiz": False}})
    quiz_attempts_col.delete_many({"lesson_id": lesson_id})
    return {"success": True}


# ---------------------------------------------------------------------------
# Quiz attempts (students)
# ---------------------------------------------------------------------------

@router.post("/submit")
async def submit_quiz(course_id: str, lesson_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Submit a quiz attempt."""
    # Verify enrollment
    enrollment = enrollments_col.find_one({"user_id": current_user["id"], "course_id": course_id})
    if not enrollment and not has_permission(current_user["role"], UserRole.FACULTY):
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    quiz = quizzes_col.find_one({"lesson_id": lesson_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")

    # Check attempt limit
    attempt_count = quiz_attempts_col.count_documents({
        "quiz_id": quiz["id"], "user_id": current_user["id"],
    })
    if attempt_count >= quiz.get("max_attempts", 3):
        raise HTTPException(status_code=400, detail=f"Maximum attempts ({quiz['max_attempts']}) reached")

    data = await request.json()
    answers = data.get("answers", {})

    # Auto-grade
    grading = _auto_grade(quiz, answers)

    passed = grading["score_percentage"] >= quiz.get("pass_threshold", 70)
    if grading["needs_manual_review"]:
        status = "pending_review"
    else:
        status = "passed" if passed else "failed"

    attempt = {
        "id": str(uuid.uuid4()),
        "quiz_id": quiz["id"],
        "course_id": course_id,
        "lesson_id": lesson_id,
        "user_id": current_user["id"],
        "user_name": current_user.get("name", ""),
        "answers": answers,
        "results": grading["results"],
        "total_points": grading["total_points"],
        "earned_points": grading["earned_points"],
        "score_percentage": grading["score_percentage"],
        "status": status,
        "attempt_number": attempt_count + 1,
        "submitted_at": datetime.now(timezone.utc),
        "reviewed_at": None,
        "reviewed_by": None,
    }
    quiz_attempts_col.insert_one(attempt)
    attempt.pop("_id", None)

    # Strip correct answers from response if quiz doesn't show them
    if not quiz.get("show_correct_answers", True):
        for r in attempt["results"]:
            r.pop("correct_answer", None)

    return attempt


@router.get("/attempts")
async def get_my_attempts(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Get the current user's quiz attempts for a lesson."""
    quiz = quizzes_col.find_one({"lesson_id": lesson_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")

    attempts = list(quiz_attempts_col.find(
        {"quiz_id": quiz["id"], "user_id": current_user["id"]},
        {"_id": 0},
    ).sort("submitted_at", -1))

    return {"attempts": attempts, "max_attempts": quiz.get("max_attempts", 3)}


@router.get("/all-attempts")
async def get_all_attempts(course_id: str, lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Get all student attempts for a quiz (instructor only)."""
    _check_course_instructor(course_id, current_user)
    quiz = quizzes_col.find_one({"lesson_id": lesson_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz for this lesson")

    attempts = list(quiz_attempts_col.find(
        {"quiz_id": quiz["id"]},
        {"_id": 0},
    ).sort("submitted_at", -1))

    return {"attempts": attempts}


@router.put("/attempts/{attempt_id}/review")
async def review_attempt(
    course_id: str, lesson_id: str, attempt_id: str,
    request: Request, current_user: dict = Depends(get_current_user),
):
    """Review and grade short-answer questions in a student's attempt (instructor only)."""
    _check_course_instructor(course_id, current_user)

    attempt = quiz_attempts_col.find_one({"id": attempt_id})
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    data = await request.json()
    reviewed_questions = data.get("reviews", {})  # {question_id: {points_earned: N, feedback: "..."}}

    results = attempt.get("results", [])
    earned = attempt.get("earned_points", 0)

    for r in results:
        if r["question_id"] in reviewed_questions:
            review = reviewed_questions[r["question_id"]]
            pts = min(review.get("points_earned", 0), r["points_possible"])
            r["points_earned"] = pts
            r["needs_review"] = False
            r["feedback"] = review.get("feedback", "")
            earned += pts

    total = attempt.get("total_points", 1)
    score_pct = round((earned / total) * 100, 1) if total > 0 else 0

    quiz = quizzes_col.find_one({"lesson_id": lesson_id})
    passed = score_pct >= quiz.get("pass_threshold", 70) if quiz else False
    still_needs_review = any(r.get("needs_review") for r in results)

    update = {
        "results": results,
        "earned_points": earned,
        "score_percentage": score_pct,
        "status": "pending_review" if still_needs_review else ("passed" if passed else "failed"),
        "reviewed_at": datetime.now(timezone.utc),
        "reviewed_by": current_user["id"],
    }
    quiz_attempts_col.update_one({"id": attempt_id}, {"$set": update})
    updated = quiz_attempts_col.find_one({"id": attempt_id}, {"_id": 0})
    return updated
