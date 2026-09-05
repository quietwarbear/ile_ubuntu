"""Email alerts to a course's teachers.

Kept out of the route modules so discussions and submissions can both reach it
without importing each other, and out of courses.py to avoid a cycle — course
staff is derived from the course document here rather than borrowed from there.

Every send is fire-and-forget and every failure is swallowed: a mail problem
must never fail the student action that triggered it.
"""

import logging
import os
from html import escape as esc

from database import users_col
from routes.email_notifications import build_email_html, send_email, send_in_background

logger = logging.getLogger(__name__)

APP_URL = os.environ.get("APP_URL", "https://ile-ubuntu.org").rstrip("/")

# Which per-teacher switch governs which kind of alert. Absent means on: a
# teacher who has never opened the setting still hears when work comes in.
PREF_FIELD = {
    "discussion": "notify_discussions",
    "submission": "notify_submissions",
}

EXCERPT_CHARS = 300


def _staff_ids(course: dict) -> list:
    ids = [course.get("instructor_id")] + list(course.get("co_instructor_ids") or [])
    return [i for i in ids if i]


def recipients(course: dict, kind: str, exclude_id: str = None) -> list:
    """Teachers who should hear about this, at the address each chose.

    Falls back to the account email when no preferred address is set, and never
    tells someone about their own action.
    """
    field = PREF_FIELD[kind]
    people = []
    for user in users_col.find(
        {"id": {"$in": _staff_ids(course)}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "notification_email": 1, field: 1},
    ):
        if exclude_id and user.get("id") == exclude_id:
            continue
        if user.get(field) is False:
            continue
        # Strip before choosing: a field holding only spaces is truthy, and
        # would otherwise win the fallback and leave the teacher unreachable.
        preferred = (user.get("notification_email") or "").strip()
        address = preferred or (user.get("email") or "").strip()
        if address:
            people.append({"name": user.get("name") or "there", "email": address})
    return people


def _excerpt(text: str) -> str:
    body = (text or "").strip()
    if len(body) > EXCERPT_CHARS:
        body = body[:EXCERPT_CHARS].rstrip() + "…"
    return esc(body).replace("\n", "<br>")


def _send(course: dict, kind: str, exclude_id, subject, title, body_html, cta_text, cta_url):
    try:
        for person in recipients(course, kind, exclude_id=exclude_id):
            html = build_email_html(title, body_html, cta_text, cta_url)
            send_in_background(send_email(person["email"], subject, html))
    except Exception as exc:  # never surface a mail problem to the student
        logger.error("Teacher alert failed for course %s: %s", course.get("id"), exc)


def notify_discussion(course: dict, topic: dict, author_name: str, content: str, *, is_new_topic: bool, exclude_id=None):
    """A topic opened, or a reply added to one."""
    course_title = course.get("title") or "your course"
    who = esc(author_name or "Someone")
    what = esc(topic.get("title") or "a topic")
    url = f"{APP_URL}/courses/{course.get('id')}"

    if is_new_topic:
        subject = f"New topic in {course_title}: {topic.get('title') or ''}".strip()
        title = "A new topic was opened"
        lead = f"<strong>{who}</strong> opened <strong>{what}</strong> in {esc(course_title)}."
    else:
        subject = f"New reply in {course_title}: {topic.get('title') or ''}".strip()
        title = "Someone replied in the discussion"
        lead = f"<strong>{who}</strong> replied to <strong>{what}</strong> in {esc(course_title)}."

    body = f"<p>{lead}</p><blockquote style=\"border-left:3px solid #D4AF37;margin:12px 0;padding:4px 0 4px 12px;color:#CBD5E1;\">{_excerpt(content)}</blockquote>"
    _send(course, "discussion", exclude_id, subject, title, body, "Open the discussion", url)


def notify_submission(course: dict, lesson: dict, student_name: str, *, is_update: bool, exclude_id=None):
    """Work handed in, or an existing submission replaced.

    The work itself is never attached or quoted — it is read in the app, where
    access is checked.
    """
    course_title = course.get("title") or "your course"
    who = esc(student_name or "A student")
    lesson_title = esc(lesson.get("title") or "a lesson")
    url = f"{APP_URL}/courses/{course.get('id')}"

    verb = "updated their work for" if is_update else "handed in work for"
    subject = f"{student_name or 'A student'} {verb} {lesson.get('title') or 'a lesson'}"
    body = (
        f"<p><strong>{who}</strong> {verb} <strong>{lesson_title}</strong> "
        f"in {esc(course_title)}.</p>"
        "<p>Open the lesson to read it.</p>"
    )
    _send(course, "submission", exclude_id, subject, "Work handed in", body, "Open the lesson", url)
