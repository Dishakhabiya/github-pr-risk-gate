from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.rag_routes import router as rag_router

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

app.include_router(router)
app.include_router(rag_router, prefix="/api")
