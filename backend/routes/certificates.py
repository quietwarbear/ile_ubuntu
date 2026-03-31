from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from database import courses_col, enrollments_col, lessons_col, users_col
from middleware import get_current_user
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import io
import uuid

router = APIRouter(prefix="/api/certificates", tags=["certificates"])

BRAND_DARK = HexColor("#050814")
BRAND_NAVY = HexColor("#0A1128")
BRAND_CARD = HexColor("#0F172A")
BRAND_GOLD = HexColor("#D4AF37")
BRAND_LIGHT = HexColor("#F8FAFC")
BRAND_MUTED = HexColor("#94A3B8")
BRAND_BORDER = HexColor("#1E293B")


def generate_certificate_pdf(student_name, course_title, completion_date, cert_id):
    buffer = io.BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    # Background
    c.setFillColor(BRAND_DARK)
    c.rect(0, 0, width, height, fill=1)

    # Inner border
    margin = 30
    c.setStrokeColor(BRAND_GOLD)
    c.setLineWidth(2)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Inner decorative border
    inner = 45
    c.setStrokeColor(BRAND_BORDER)
    c.setLineWidth(0.5)
    c.rect(inner, inner, width - 2 * inner, height - 2 * inner)

    # Corner decorations (gold dots)
    for x, y in [(margin + 15, margin + 15), (width - margin - 15, margin + 15),
                 (margin + 15, height - margin - 15), (width - margin - 15, height - margin - 15)]:
        c.setFillColor(BRAND_GOLD)
        c.circle(x, y, 4, fill=1)

    # Ankh symbol (top center)
    cx = width / 2
    c.setFillColor(BRAND_GOLD)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(cx, height - 100, "\u2625")

    # "The Ile Ubuntu" header
    c.setFillColor(BRAND_GOLD)
    c.setFont("Helvetica", 10)
    c.drawCentredString(cx, height - 120, "THE ILE UBUNTU")

    # Certificate of Completion
    c.setFillColor(BRAND_LIGHT)
    c.setFont("Helvetica", 14)
    c.drawCentredString(cx, height - 155, "CERTIFICATE OF COMPLETION")

    # Decorative gold line
    c.setStrokeColor(BRAND_GOLD)
    c.setLineWidth(1)
    c.line(cx - 120, height - 165, cx + 120, height - 165)

    # "This certifies that"
    c.setFillColor(BRAND_MUTED)
    c.setFont("Helvetica", 11)
    c.drawCentredString(cx, height - 195, "This certifies that")

    # Student name
    c.setFillColor(BRAND_LIGHT)
    c.setFont("Helvetica-Bold", 28)
    # Truncate long names
    display_name = student_name if len(student_name) <= 35 else student_name[:32] + "..."
    c.drawCentredString(cx, height - 235, display_name)

    # Gold underline under name
    name_width = c.stringWidth(display_name, "Helvetica-Bold", 28)
    c.setStrokeColor(BRAND_GOLD)
    c.setLineWidth(0.8)
    c.line(cx - name_width / 2, height - 242, cx + name_width / 2, height - 242)

    # "has successfully completed"
    c.setFillColor(BRAND_MUTED)
    c.setFont("Helvetica", 11)
    c.drawCentredString(cx, height - 268, "has successfully completed the course")

    # Course title
    c.setFillColor(BRAND_GOLD)
    c.setFont("Helvetica-Bold", 20)
    display_title = course_title if len(course_title) <= 45 else course_title[:42] + "..."
    c.drawCentredString(cx, height - 300, display_title)

    # "on the Living Learning Commons"
    c.setFillColor(BRAND_MUTED)
    c.setFont("Helvetica", 10)
    c.drawCentredString(cx, height - 325, "on the Living Learning Commons platform")

    # Date
    c.setFillColor(BRAND_LIGHT)
    c.setFont("Helvetica", 12)
    c.drawCentredString(cx, height - 365, completion_date)

    # Bottom section - two columns
    left_x = margin + 80
    right_x = width - margin - 80

    # Left: Certificate ID
    c.setFillColor(BRAND_MUTED)
    c.setFont("Helvetica", 7)
    c.drawCentredString(left_x, margin + 50, "CERTIFICATE ID")
    c.setFillColor(BRAND_LIGHT)
    c.setFont("Helvetica", 8)
    c.drawCentredString(left_x, margin + 38, cert_id[:16])

    # Right: Signature line
    c.setStrokeColor(BRAND_BORDER)
    c.setLineWidth(0.5)
    c.line(right_x - 60, margin + 55, right_x + 60, margin + 55)
    c.setFillColor(BRAND_MUTED)
    c.setFont("Helvetica", 7)
    c.drawCentredString(right_x, margin + 42, "THE ILE UBUNTU")

    # Footer
    c.setFillColor(HexColor("#475569"))
    c.setFont("Helvetica", 7)
    c.drawCentredString(cx, margin + 12, "The Ile Ubuntu \u2014 Living Learning Commons \u2014 Knowledge \u2022 Community \u2022 Culture")

    c.save()
    buffer.seek(0)
    return buffer


@router.get("/check/{course_id}")
async def check_certificate(course_id: str, current_user: dict = Depends(get_current_user)):
    """Check if user is eligible for a certificate."""
    enrollment = enrollments_col.find_one(
        {"user_id": current_user["id"], "course_id": course_id},
        {"_id": 0}
    )
    if not enrollment:
        return {"eligible": False, "reason": "Not enrolled"}

    progress = enrollment.get("progress", 0)
    if progress < 100:
        return {"eligible": False, "reason": f"Progress: {progress}%", "progress": progress}

    return {
        "eligible": True,
        "progress": 100,
        "completed_at": enrollment.get("completed_at", enrollment.get("enrolled_at")),
    }


@router.get("/download/{course_id}")
async def download_certificate(course_id: str, current_user: dict = Depends(get_current_user)):
    """Generate and download a certificate PDF."""
    enrollment = enrollments_col.find_one(
        {"user_id": current_user["id"], "course_id": course_id},
        {"_id": 0}
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")

    if enrollment.get("progress", 0) < 100:
        raise HTTPException(status_code=400, detail="Course not yet completed")

    course = courses_col.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    cert_id = str(uuid.uuid4())
    completed_at = enrollment.get("completed_at") or enrollment.get("enrolled_at")
    if completed_at:
        if isinstance(completed_at, str):
            try:
                date_str = datetime.fromisoformat(completed_at.replace("Z", "+00:00")).strftime("%B %d, %Y")
            except (ValueError, TypeError):
                date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        else:
            date_str = completed_at.strftime("%B %d, %Y")
    else:
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    pdf_buffer = generate_certificate_pdf(
        student_name=current_user.get("name", "Student"),
        course_title=course.get("title", "Course"),
        completion_date=date_str,
        cert_id=cert_id,
    )

    filename = f"certificate_{course['title'].replace(' ', '_')[:30]}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/my-certificates")
async def list_my_certificates(current_user: dict = Depends(get_current_user)):
    """List all completed courses (eligible for certificates)."""
    completed = list(enrollments_col.find(
        {"user_id": current_user["id"], "progress": 100},
        {"_id": 0}
    ))

    certs = []
    for enr in completed:
        course = courses_col.find_one({"id": enr["course_id"]}, {"_id": 0, "id": 1, "title": 1, "description": 1})
        if course:
            certs.append({
                "course_id": course["id"],
                "course_title": course["title"],
                "completed_at": enr.get("completed_at") or enr.get("enrolled_at"),
            })

    return certs
