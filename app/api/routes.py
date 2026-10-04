import logging
from fastapi import APIRouter, HTTPException, status

from app.api.schemas import (
    AnalyzeCommitRequest,
    AnalyzeCommitResponse,
    AnalyzePRRequest,
    AnalyzePRResponse,
    HealthResponse,
)
from app.features.extractor import extract_features
from app.github.commit_service import fetch_commit_details
from app.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.github.pr_service import fetch_pr_details
from app.preprocessing.diff_processor import preprocess_diff
from ml.predict import predict_pr_risk

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    """Health check endpoint returning API operational status."""
    return HealthResponse(status="ok")


@router.post(
    "/api/pr/analyze",
    response_model=AnalyzePRResponse,
    status_code=status.HTTP_200_OK,
    tags=["PR Analysis"],
)
def analyze_pull_request(payload: AnalyzePRRequest) -> AnalyzePRResponse:
    """Analyze a GitHub Pull Request and return risk prediction & statistics.

    Flow:
        1. Fetch PR details using US-01 GitHub client.
        2. Preprocess unified diff using US-02.
        3. Extract creation-time numeric features using US-03.
        4. Predict risk probability & label using US-07 pre-trained ML model.
    """
    owner, repo = payload.repository.strip().split("/", 1)
    pr_number = payload.pr_number

    try:
        # 1. US-01: Ingest PR metadata & diff
        pr_data = fetch_pr_details(owner, repo, pr_number)

        # 2. US-02: Preprocess raw unified diff
        diff_data = preprocess_diff(pr_data.get("diff", ""))

        # 3. US-03: Feature extraction
        features = extract_features(pr_data, diff_data)

        # 4. US-07: Risk prediction using pre-trained ML artifact
        risk_prediction = predict_pr_risk(pr_data, diff_data)

        return AnalyzePRResponse(
            repository=f"{owner}/{repo}",
            pr_number=pr_number,
            title=pr_data.get("title", ""),
            description=pr_data.get("body") or "",
            files_changed=len(diff_data.get("files_changed", [])),
            lines_added=diff_data.get("num_added_lines", 0),
            lines_deleted=diff_data.get("num_deleted_lines", 0),
            commits=features.get("commits_count", 0),
            features=features,
            risk_score=risk_prediction.get("risk_score", 0.0),
            risk_level=risk_prediction.get("risk_level", "LOW"),
            model_name=risk_prediction.get("model_name", "Logistic Regression"),
        )

    except GitHubNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository or Pull Request not found: {owner}/{repo}#{pr_number}",
        )
    except GitHubAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub authentication failed. Please verify your GITHUB_TOKEN configuration.",
        )
    except GitHubRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="GitHub API rate limit exceeded. Please try again later.",
        )
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API communication failure.",
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk prediction model artifact not found. Please train the model artifact first.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error analyzing Pull Request %s/%s#%s", owner, repo, pr_number)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the Pull Request.",
        )


@router.post(
    "/api/commit/analyze",
    response_model=AnalyzeCommitResponse,
    status_code=status.HTTP_200_OK,
    tags=["Commit Analysis"],
)
def analyze_commit(payload: AnalyzeCommitRequest) -> AnalyzeCommitResponse:
    """Analyze a GitHub Commit and return risk prediction & statistics.

    Flow:
        1. Fetch commit details & diff from GitHub.
        2. Preprocess unified diff.
        3. Extract creation-time numeric features.
        4. Predict risk probability & label using existing ML model.
    """
    owner, repo = payload.repository.strip().split("/", 1)
    commit_sha = payload.commit_sha.strip()

    try:
        commit_data = fetch_commit_details(owner, repo, commit_sha)
        diff_data = preprocess_diff(commit_data.get("diff", ""))
        features = extract_features(commit_data, diff_data)
        risk_prediction = predict_pr_risk(commit_data, diff_data)

        return AnalyzeCommitResponse(
            repository=f"{owner}/{repo}",
            commit_sha=commit_data.get("sha", commit_sha),
            short_sha=commit_data.get("short_sha", commit_sha[:7]),
            commit_message=commit_data.get("title", ""),
            author=commit_data.get("author", ""),
            files_changed=len(diff_data.get("files_changed", [])),
            lines_added=diff_data.get("num_added_lines", 0),
            lines_deleted=diff_data.get("num_deleted_lines", 0),
            commits=1,
            features=features,
            risk_score=risk_prediction.get("risk_score", 0.0),
            risk_level=risk_prediction.get("risk_level", "LOW"),
            model_name=risk_prediction.get("model_name", "Logistic Regression"),
            analysis_type="Commit Risk Analysis",
        )

    except GitHubNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository or Commit not found: {owner}/{repo}@{commit_sha}",
        )
    except GitHubAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub authentication failed. Please verify your token configuration.",
        )
    except GitHubRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="GitHub API rate limit exceeded. Please try again later.",
        )
    except GitHubAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API communication failure.",
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk prediction model artifact not found. Please train the model artifact first.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error analyzing Commit %s/%s@%s", owner, repo, commit_sha)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the Commit.",
        )


