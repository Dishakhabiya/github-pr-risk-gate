from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""

    status: str = "ok"


class AnalyzePRRequest(BaseModel):
    """Request schema for /api/pr/analyze endpoint."""

    repository: str = Field(
        ...,
        example="kubernetes/kubernetes",
        description="GitHub repository in 'owner/repo' format.",
    )
    pr_number: int = Field(
        ...,
        example=142645,
        description="Pull Request number.",
    )

    @field_validator("repository")
    def validate_repository_format(cls, v: str) -> str:
        v_clean = v.strip()
        if not v_clean or "/" not in v_clean:
            raise ValueError("Repository must be provided in 'owner/repo' format (e.g. 'kubernetes/kubernetes').")
        parts = v_clean.split("/")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise ValueError("Repository must contain valid owner and repository names.")
        return v_clean

    @field_validator("pr_number")
    def validate_pr_number(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Pull Request number must be a positive integer greater than 0.")
        return v


class AnalyzePRResponse(BaseModel):
    """Response schema for /api/pr/analyze endpoint."""

    repository: str
    pr_number: int
    title: str
    description: str
    files_changed: int
    lines_added: int
    lines_deleted: int
    commits: int
    features: Dict[str, Any]
    risk_score: float
    risk_level: str
    model_name: Optional[str] = "Logistic Regression"
