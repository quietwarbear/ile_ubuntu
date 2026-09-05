import os
import asyncio
import logging
import resend
from fastapi import APIRouter, HTTPException, Depends, Request
from dotenv import load_dotenv
from database import users_col
from middleware import get_current_user

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications/email", tags=["email"])

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://www.ile-ubuntu.org").rstrip("/")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Branded HTML email template
def build_email_html(title, body_html, cta_text=None, cta_url=None):
    cta_block = ""
    if cta_text and cta_url:
        cta_block = f'''
        <tr><td style="padding:20px 30px 0;">
          <a href="{cta_url}" style="display:inline-block;background:#D4AF37;color:#050814;
            padding:10px 24px;border-radius:4px;text-decoration:none;font-weight:600;font-size:14px;">
            {cta_text}
          </a>
        </td></tr>'''

    return f'''
    <div style="background:#050814;padding:30px 0;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;background:#0F172A;border-radius:8px;border:1px solid #1E293B;">
        <tr><td style="padding:24px 30px 16px;border-bottom:1px solid #1E293B;">
          <span style="color:#D4AF37;font-size:18px;font-weight:700;letter-spacing:1px;">&#9775; The Ile Ubuntu</span>
        </td></tr>
        <tr><td style="padding:24px 30px 8px;">
          <h2 style="color:#F8FAFC;font-size:20px;margin:0 0 12px;">{title}</h2>
          <div style="color:#94A3B8;font-size:14px;line-height:1.6;">{body_html}</div>
        </td></tr>
        {cta_block}
        <tr><td style="padding:24px 30px;border-top:1px solid #1E293B;margin-top:20px;">
          <p style="color:#475569;font-size:11px;margin:0;">The Ile Ubuntu &mdash; Living Learning Commons</p>
        </td></tr>
      </table>
    </div>'''


async def send_email(to_email, subject, html):
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured, skipping email")
        return None
    params = {
        "from": SENDER_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email}: {result.get('id', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return None


def send_in_background(coro):
    """Fire-and-forget an async email coroutine from a sync (threadpool) handler.

    Route handlers that do blocking DB work are sync and run in FastAPI's
    threadpool, where asyncio.create_task() fails (no running event loop).
    This runs the coroutine on a short-lived daemon thread instead.
    """
    import threading

    def _run():
        try:
            asyncio.run(coro)
        except Exception as e:
            logger.error(f"Background email failed: {e}")

    threading.Thread(target=_run, daemon=True).start()


async def send_enrollment_email(user_email, user_name, course_title, course_id):
    html = build_email_html(
        "You're Enrolled!",
        f"<p>Welcome, <strong>{user_name}</strong>! You've successfully enrolled in:</p>"
        f"<p style='color:#D4AF37;font-size:16px;font-weight:600;'>{course_title}</p>"
        f"<p>Start your learning journey now.</p>",
        "Go to Course",
        f"{PUBLIC_SITE_URL}/courses/{course_id}",
    )
    await send_email(user_email, f"Enrolled: {course_title}", html)


async def send_course_access_email(user_email, user_name, course_title, course_id):
    """Welcome/access email after a PAID course purchase. Leads with the
    direct class link — an unlisted class is reachable only through it, so
    this email is the student's key to the room."""
    class_url = f"{PUBLIC_SITE_URL}/courses/{course_id}"
    html = build_email_html(
        "Your Class Is Ready",
        f"<p>Welcome, <strong>{user_name}</strong>! Your payment is confirmed and "
        f"you're enrolled in:</p>"
        f"<p style='color:#D4AF37;font-size:16px;font-weight:600;'>{course_title}</p>"
        f"<p><strong>Your direct class link:</strong><br>"
        f"<a href='{class_url}' style='color:#D4AF37;'>{class_url}</a></p>"
        f"<p>Save this email. If your class is unlisted, it will not appear in the "
        f"public course list — use this link (or My Classes after signing in) to "
        f"get back to it.</p>",
        "Open Your Class",
        class_url,
    )
    await send_email(user_email, f"You're in: {course_title}", html)


async def send_lesson_complete_email(user_email, user_name, lesson_title, course_title):
    html = build_email_html(
        "Lesson Complete",
        f"<p>Great work, <strong>{user_name}</strong>! You completed:</p>"
        f"<p style='color:#D4AF37;font-size:16px;font-weight:600;'>{lesson_title}</p>"
        f"<p>in <em>{course_title}</em>. Keep going!</p>",
    )
    await send_email(user_email, f"Completed: {lesson_title}", html)


async def send_cohort_join_email(user_email, user_name, cohort_name):
    html = build_email_html(
        "Welcome to the Cohort",
        f"<p><strong>{user_name}</strong>, you've joined:</p>"
        f"<p style='color:#D4AF37;font-size:16px;font-weight:600;'>{cohort_name}</p>"
        f"<p>Connect with your peers and explore linked courses.</p>",
    )
    await send_email(user_email, f"Joined: {cohort_name}", html)


async def send_live_session_reminder(user_email, user_name, session_title, scheduled_for):
    html = build_email_html(
        "Live Session Starting Soon",
        f"<p><strong>{user_name}</strong>, a live session is about to begin:</p>"
        f"<p style='color:#D4AF37;font-size:16px;font-weight:600;'>{session_title}</p>"
        f"<p>Scheduled: {scheduled_for}</p>",
    )
    await send_email(user_email, f"Live: {session_title}", html)


# Test endpoint
@router.post("/test")
async def test_email(current_user: dict = Depends(get_current_user)):
    if not RESEND_API_KEY:
        raise HTTPException(status_code=500, detail="Email service not configured")

    result = await send_email(
        current_user.get("email", ""),
        "Test Email from The Ile Ubuntu",
        build_email_html(
            "Email System Active",
            f"<p>Hello <strong>{current_user.get('name', 'User')}</strong>,</p>"
            "<p>Your email notifications are working correctly.</p>",
        ),
    )
    if result:
        return {"success": True, "email_id": result.get("id")}
    raise HTTPException(status_code=500, detail="Failed to send test email")


# --- Per-teacher alert preferences ---

# Absent means on. A teacher who has never opened this still hears when a
# student hands work in, which is the behaviour they expect by default.
_PREF_DEFAULTS = {"notify_discussions": True, "notify_submissions": True}


def _preferences(user_doc: dict) -> dict:
    return {
        "notification_email": (user_doc.get("notification_email") or "").strip(),
        "account_email": user_doc.get("email", ""),
        **{k: user_doc.get(k, default) is not False for k, default in _PREF_DEFAULTS.items()},
    }


@router.get("/preferences")
def get_email_preferences(current_user: dict = Depends(get_current_user)):
    """Where this teacher wants alerts sent, and which ones they want."""
    doc = users_col.find_one({"id": current_user["id"]}, {"_id": 0}) or {}
    return _preferences(doc)


@router.put("/preferences")
async def set_email_preferences(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    update = {}

    if "notification_email" in data:
        # Empty clears it and falls back to the account address. Deliberately a
        # shape check, not validation theatre — Resend reports real failures.
        address = (data.get("notification_email") or "").strip()
        if address and ("@" not in address or address.startswith("@") or address.endswith("@")):
            raise HTTPException(status_code=400, detail="That does not look like an email address")
        update["notification_email"] = address

    for field in _PREF_DEFAULTS:
        if field in data:
            update[field] = bool(data[field])

    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")

    users_col.update_one({"id": current_user["id"]}, {"$set": update})
    doc = users_col.find_one({"id": current_user["id"]}, {"_id": 0}) or {}
    return {"success": True, **_preferences(doc)}
