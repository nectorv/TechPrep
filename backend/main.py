import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, coach, interview, dashboard, plans

logger = logging.getLogger(__name__)

app = FastAPI(title="TechPrep API", version="0.1.0")

_origins = ["http://localhost:5173", "http://localhost:5174"]
if os.getenv("FRONTEND_URL"):
    # Strip all whitespace including hidden/zero-width characters
    _frontend_url = "".join(os.getenv("FRONTEND_URL").split()).rstrip("/")
    _origins.append(_frontend_url)

logger.warning("CORS allowed origins: %s", _origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth",      tags=["auth"])
app.include_router(plans.router,     prefix="/api/plans",     tags=["plans"])
app.include_router(coach.router,     prefix="/api/coach",     tags=["coach"])
app.include_router(interview.router, prefix="/api/interview", tags=["interview"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


@app.get("/health")
def health():
    return {"status": "ok"}
