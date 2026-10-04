import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import router
from app.api.rag_routes import router as rag_router
from app.api.auth_routes import router as auth_router
from app.api.github_routes import router as github_router

load_dotenv()

app = FastAPI(
    title="GitHub PR Risk Gate API",
    description="Person 1 API Integration Layer for PR Ingestion, Feature Extraction & Risk Prediction",
    version="1.0.0",
)

# Enable CORS for local React development frontend (ports 5173 & 5174)
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_secret = os.getenv("SESSION_SECRET_KEY", "github-pr-risk-gate-dev-secret-key")
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="session",
    max_age=14 * 24 * 3600,
    same_site="lax",
    https_only=False,
)

import time
import logging
from fastapi import Request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("monitoring")

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    """US-21: Basic Monitoring Middleware."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"Path: {request.url.path} | Method: {request.method} | "
        f"Status: {response.status_code} | Latency: {process_time:.4f}s"
    )
    return response

app.include_router(router)
app.include_router(rag_router, prefix="/api")
app.include_router(auth_router)
app.include_router(github_router)
