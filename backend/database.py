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
