"""Emailed sign-in links (item I3).

A link is a single-use token. Only its SHA-256 hash is stored, and redeeming
it is one atomic find-and-update, so two clicks can't both get in.

Two kinds:
- "signin": asked for on the sign-in page. Expires in 15 minutes.
- "welcome": sent when an organizer enrolls someone (I1 import). Expires in
  3 days, because people open welcome emails hours or days later. Once it has
  expired the page offers to email a fresh 15-minute link.

The link opens the web page /signin-link. Redeeming happens there by a POST
when the person presses the button — not on page load — so mail scanners
that open links before the person does can't use the token up. On a phone
the page can hand the session to the installed app through the
ileubuntu://auth/email/callback deep link, which the app already handles
(the same way Google sign-in returns), so no new app build is needed.
"""

import hashlib
import html as html_lib
import os
import secrets
from datetime import datetime, timedelta, timezone

from database import email_signin_tokens_col, users_col

PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://www.ile-ubuntu.org").rstrip("/")

SIGNIN_TTL = timedelta(minutes=15)
WELCOME_TTL = timedelta(days=3)
TTL_BY_PURPOSE = {"signin": SIGNIN_TTL, "welcome": WELCOME_TTL}

# Per address, on top of the per-IP limit on the route: at most this many
# sign-in links in the window, so nobody can flood one inbox from many IPs.
MAX_LINKS_PER_ADDRESS = 3
ADDRESS_WINDOW = timedelta(minutes=15)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utc(value):
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def issue_token(user_id: str, purpose: str = "signin", now: datetime = None) -> str:
    """Store a new link token for this user and return the raw token (only
    ever put in the email)."""
    if purpose not in TTL_BY_PURPOSE:
        raise ValueError(f"unknown sign-in link purpose {purpose!r}")
    now = now or datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    email_signin_tokens_col.insert_one({
        "token_hash": _hash(token),
        "user_id": user_id,
        "purpose": purpose,
        "used": False,
        "created_at": now,
        "expires_at": now + TTL_BY_PURPOSE[purpose],
    })
    return token


def recent_link_count(user_id: str, now: datetime = None) -> int:
    now = now or datetime.now(timezone.utc)
    return email_signin_tokens_col.count_documents({
        "user_id": user_id, "purpose": "signin", "created_at": {"$gte": now - ADDRESS_WINDOW},
    })


def redeem_token(token: str, now: datetime = None):
    """Use the token up and return its user, or None if it is unknown, used
    or expired. Atomic: of two simultaneous redeems only one succeeds."""
    if not token or not isinstance(token, str):
        return None
    now = now or datetime.now(timezone.utc)
    record = email_signin_tokens_col.find_one_and_update(
        {"token_hash": _hash(token.strip()), "used": False, "expires_at": {"$gt": now}},
        {"$set": {"used": True, "used_at": now}},
    )
    if not record:
        return None
    user = users_col.find_one({"id": record["user_id"]}, {"_id": 0})
    if user and not user.get("email_verified"):
        # Getting here proves the person reads that inbox.
        users_col.update_one({"id": user["id"]}, {"$set": {"email_verified": True}})
    return user


def token_state(token: str, now: datetime = None) -> str:
    """"valid", "used", "expired" or "unknown" — without using it up. Lets
    the page say the right thing before the person presses the button."""
    if not token:
        return "unknown"
    now = now or datetime.now(timezone.utc)
    record = email_signin_tokens_col.find_one({"token_hash": _hash(token.strip())})
    if not record:
        return "unknown"
    if record.get("used"):
        return "used"
    if _utc(record["expires_at"]) <= now:
        return "expired"
    return "valid"


def signin_url(token: str, app: bool = False) -> str:
    url = f"{PUBLIC_SITE_URL}/signin-link?token={token}"
    return url + "&app=1" if app else url


def signin_email(name: str, url: str):
    """(subject, html) for a link asked for on the sign-in page."""
    from routes.email_notifications import build_email_html
    html = build_email_html(
        "Your sign-in link",
        f"<p>Hello, <strong>{html_lib.escape(name or '')}</strong>. Use the button below to sign in "
        f"to The Ile Ubuntu. It works once and expires in 15 minutes.</p>"
        f"<p>If you didn't ask for this, you can ignore this email; nobody can sign in without it.</p>",
        "Sign in",
        url,
    )
    return "Your sign-in link — The Ile Ubuntu", html


def welcome_email(name: str, course_titles: list, url: str):
    """(subject, html) for someone an organizer just enrolled."""
    from routes.email_notifications import build_email_html
    items = "".join(
        f"<li style='color:#D4AF37;font-size:15px;font-weight:600;'>{html_lib.escape(t or 'Your course')}</li>"
        for t in course_titles
    )
    one = len(course_titles) == 1
    html = build_email_html(
        "You're enrolled",
        f"<p>Welcome, <strong>{html_lib.escape(name or '')}</strong>! You've been enrolled in "
        f"{'this course' if one else 'these courses'}:</p>"
        f"<ul style='padding-left:18px;'>{items}</ul>"
        f"<p>The button below signs you in — no password needed. It works once and expires in "
        f"3 days. After that, choose <em>Email me a sign-in link</em> on the sign-in page, or "
        f"sign in with Google using this email address.</p>",
        "Sign in and start",
        url,
    )
    subject = (f"You're enrolled: {course_titles[0]}" if one
               else f"You're enrolled in {len(course_titles)} courses")
    return subject, html
