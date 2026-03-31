from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="The Ile Ubuntu API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Import and register routers
from routes.auth import router as auth_router
from routes.courses import router as courses_router
from routes.cohorts import router as cohorts_router
from routes.community import router as community_router
from routes.archives import router as archives_router
from routes.files import router as files_router
from routes.messages import router as messages_router
from routes.enrollments import router as enrollments_router
from routes.live_sessions import router as live_sessions_router

app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(cohorts_router)
app.include_router(community_router)
app.include_router(archives_router)
app.include_router(files_router)
app.include_router(messages_router)
app.include_router(enrollments_router)
app.include_router(live_sessions_router)


@app.get("/")
async def root():
    return {"message": "The Ile Ubuntu API v2.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
