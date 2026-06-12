import os
from pymongo import MongoClient

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'ile_ubuntu')

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_col = db.users
sessions_col = db.sessions
courses_col = db.courses
lessons_col = db.lessons
cohorts_col = db.cohorts
posts_col = db.community_posts
archives_col = db.archives
files_col = db.files
messages_col = db.messages
notifications_col = db.notifications
google_tokens_col = db.google_tokens
enrollments_col = db.enrollments
live_sessions_col = db.live_sessions
spaces_col = db.spaces
payment_transactions_col = db.payment_transactions
blog_posts_col = db.blog_posts
blog_comments_col = db.blog_comments

# Course feature collections
lesson_comments_col = db.lesson_comments
quizzes_col = db.quizzes
quiz_attempts_col = db.quiz_attempts

# Auth feature collections
password_resets_col = db.password_resets

# Activity event stream (append-only; substrate for analytics + Ubuntu Intelligence)
events_col = db.events

# Attendance v0 (one record per session+user; eval §10 Quick Win 4)
attendance_col = db.attendance

# Course invite codes (closed-ecosystem joining)
course_invites_col = db.course_invites

# Family: guardian <-> youth links (minor-safety foundation)
family_links_col = db.family_links

# Weekly family digest send log (idempotency: one digest per guardian per week)
digest_log_col = db.digest_log

# SEL check-ins (scores feed dashboard wellness; notes stay private)
checkins_col = db.checkins

# Mentorship: faculty-blessed mentor <-> mentee pairings + shared goals/journal
mentorship_pairs_col = db.mentorship_pairs
mentorship_goals_col = db.mentorship_goals
mentorship_notes_col = db.mentorship_notes


def ensure_indexes():
    """Create the indexes the hot query paths rely on. Idempotent; called at startup.

    Each index is wrapped so one conflict (e.g. legacy duplicate data blocking a
    unique index) never prevents the rest from being created or the app from booting.
    """
    import logging

    logger = logging.getLogger(__name__)

    specs = [
        # Auth: two lookups on EVERY authenticated request (middleware.py)
        (sessions_col, [("session_id", 1)], {"unique": True}),
        # TTL: Mongo auto-deletes sessions once expires_at passes
        (sessions_col, [("expires_at", 1)], {"expireAfterSeconds": 0}),
        (users_col, [("id", 1)], {"unique": True}),
        (users_col, [("email", 1)], {}),
        # Enrollments: per-user, per-course, and the pair (enroll/progress checks)
        (enrollments_col, [("user_id", 1), ("course_id", 1)], {}),
        (enrollments_col, [("course_id", 1)], {}),
        # Primary id lookups + list sorts
        (courses_col, [("id", 1)], {"unique": True}),
        (courses_col, [("status", 1), ("created_at", -1)], {}),
        (lessons_col, [("course_id", 1)], {}),
        (lessons_col, [("id", 1)], {}),
        (posts_col, [("id", 1)], {"unique": True}),
        (posts_col, [("category", 1), ("created_at", -1)], {}),
        (posts_col, [("created_at", -1)], {}),
        (blog_posts_col, [("slug", 1)], {}),
        (blog_posts_col, [("created_at", -1)], {}),
        (blog_comments_col, [("post_id", 1)], {}),
        (cohorts_col, [("id", 1)], {"unique": True}),
        (spaces_col, [("id", 1)], {"unique": True}),
        (archives_col, [("id", 1)], {}),
        (files_col, [("id", 1)], {}),
        (live_sessions_col, [("id", 1)], {}),
        (lesson_comments_col, [("lesson_id", 1)], {}),
        (quizzes_col, [("id", 1)], {}),
        (quizzes_col, [("course_id", 1)], {}),
        (quiz_attempts_col, [("quiz_id", 1), ("user_id", 1)], {}),
        (payment_transactions_col, [("session_id", 1)], {}),
        (payment_transactions_col, [("user_id", 1)], {}),
        (google_tokens_col, [("user_id", 1)], {}),
        (notifications_col, [("user_id", 1)], {}),
        (messages_col, [("created_at", -1)], {}),
        # Password reset tokens: lookup by token hash, TTL on expiry
        (password_resets_col, [("token_hash", 1)], {}),
        (password_resets_col, [("expires_at", 1)], {"expireAfterSeconds": 0}),
        # Activity event stream: per-user timelines, per-type trends, per-entity history
        (events_col, [("user_id", 1), ("created_at", -1)], {}),
        (events_col, [("type", 1), ("created_at", -1)], {}),
        (events_col, [("entity_type", 1), ("entity_id", 1), ("created_at", -1)], {}),
        (events_col, [("created_at", -1)], {}),
        # Attendance: one record per session+user; per-user history
        (attendance_col, [("session_id", 1), ("user_id", 1)], {"unique": True}),
        (attendance_col, [("user_id", 1), ("marked_at", -1)], {}),
        # Course invites: resolve by code, list per course
        (course_invites_col, [("code", 1)], {"unique": True}),
        (course_invites_col, [("course_id", 1)], {}),
        # Family links: one per guardian+youth pair, lookups from both sides
        (family_links_col, [("guardian_id", 1), ("youth_id", 1)], {"unique": True}),
        (family_links_col, [("youth_id", 1)], {}),
        (users_col, [("family_code", 1)], {"sparse": True}),
        # Digest log: idempotent weekly sends (duplicate triggers are no-ops)
        (digest_log_col, [("guardian_id", 1), ("week_key", 1)], {"unique": True}),
        # Mentorship: pair uniqueness + lookups from both sides + per-pairing content
        (mentorship_pairs_col, [("mentor_id", 1), ("mentee_id", 1)], {"unique": True}),
        (mentorship_pairs_col, [("mentee_id", 1)], {}),
        (mentorship_goals_col, [("pairing_id", 1)], {}),
        (mentorship_notes_col, [("pairing_id", 1), ("created_at", -1)], {}),
        # Check-ins: one per user per day; window queries for wellness
        (checkins_col, [("user_id", 1), ("day", -1)], {"unique": True}),
    ]

    for col, keys, kwargs in specs:
        try:
            col.create_index(keys, background=True, **kwargs)
        except Exception as e:
            logger.warning("Index %s on %s skipped: %s", keys, col.name, e)
