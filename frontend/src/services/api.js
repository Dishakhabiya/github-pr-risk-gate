/**
 * Mock API Layer for GitHub PR Risk Gate & Understanding System.
 * Modular service layer simulating responses for Person 1 (ML Risk), Person 2 (RAG), and Person 3 (LLM Decision).
 * Easily replaceable with real FastAPI endpoints in production.
 */

import { MOCK_PRS, DEFAULT_PR_KEY } from "../mock/mockData";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const delay = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms));

const getKey = (repo, number) => {
  if (!repo || !number) return DEFAULT_PR_KEY;
  const formattedRepo = repo.trim().toLowerCase();
  const key = `${formattedRepo}#${number}`;

  // Match existing keys case-insensitively or return fallback
  const foundKey = Object.keys(MOCK_PRS).find(
    (k) => k.toLowerCase() === key
  );
  return foundKey || DEFAULT_PR_KEY;
};

/**
 * Step 1: Ingest and Analyze PR metadata via FastAPI Person 1 endpoint
 */
export async function analyzePR(repository, prNumber) {
  if (!repository || !repository.trim()) {
    throw new Error("Please enter a Repository (e.g., kubernetes/kubernetes).");
  }
  if (prNumber === undefined || prNumber === null || String(prNumber).trim() === "") {
    throw new Error("Please enter a PR Number.");
  }

  const numericPrNumber = Number(prNumber);
  if (isNaN(numericPrNumber) || numericPrNumber <= 0) {
    throw new Error("Please enter a valid positive PR Number.");
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/pr/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        repository: repository.trim(),
        pr_number: numericPrNumber,
      }),
    });
  } catch (err) {
    throw new Error(
      `Unable to connect to the backend server at ${API_BASE_URL}. Please verify that FastAPI is running.`
    );
  }

  if (!response.ok) {
    let errorDetail = "An unexpected error occurred while analyzing the Pull Request.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch (_) {
      // Ignore JSON parse failure on non-JSON response
    }
    if (response.status === 404) {
      errorDetail = `Pull request #${numericPrNumber} not found or no longer available in repository '${repository}'.`;
    }
    throw new Error(errorDetail);
  }


  const data = await response.json();

  return {
    pr_id: data.pr_number,
    repository: data.repository,
    title: data.title,
    body: data.description,
    description: data.description,
    state: "open",
    author: "GitHub Contributor",
    base_branch: "main",
    head_branch: "patch",
    created_at: new Date().toISOString(),
    files_changed: data.files_changed,
    lines_added: data.lines_added,
    lines_deleted: data.lines_deleted,
    commits: data.commits,
    features: data.features,
    risk_score: data.risk_score,
    risk_level: data.risk_level,
    model_name: data.model_name,
    threshold: 0.5,
    changed_files_list: []
  };
}

/**
 * Step 2: Person 1 ML Risk Prediction
 */
export async function getRiskPrediction(repository, prNumber) {
  await delay(400);
  const key = getKey(repository, prNumber);
  const pr = MOCK_PRS[key];

  return {
    pr_id: pr.pr_id,
    repository: pr.repository,
    title: pr.title,
    features: pr.features,
    risk_score: pr.risk_analysis.risk_score,
    risk_level: pr.risk_analysis.risk_level,
    threshold: pr.risk_analysis.threshold,
    model_name: pr.risk_analysis.model_name
  };
}

/**
 * Step 3: Person 2 Repository Context & Questions (RAG)
 */
export async function getRepositoryContext(repository, prNumber) {
  await delay(300);
  const key = getKey(repository, prNumber);
  const pr = MOCK_PRS[key];
  return {
    repository_context: pr.repository_context
  };
}

export async function getQuestions(prData) {
  let response;
  const changedFiles = Array.isArray(prData.files_changed)
    ? prData.files_changed
    : (prData.changed_files_list ? prData.changed_files_list.map((f) => f.filename) : []);

  try {
    // Generate questions for this PR using US-11 endpoint
    response = await fetch(`${API_BASE_URL}/api/rag/pr/questions?num_questions=3`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        repository: prData.repository,
        title: prData.title || `PR ${prData.pr_id}`,
        description: prData.body || prData.description || "",
        changed_files: changedFiles,
      }),
    });
  } catch (err) {
    throw new Error(`Unable to fetch questions from ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    let errorDetail = "Failed to generate PR questions.";
    try {
      const errData = await response.json();
      if (errData && errData.detail) {
        errorDetail = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch (_) { }
    throw new Error(errorDetail);
  }

  const data = await response.json();
  return {
    questions: data.questions,
    sample_answers: {}
  };
}

/**
 * Step 4: Submit Developer Answers & Obtain Person 3 Final LLM Evaluation
 *
 * answersPayload - pre-built structured array from App.buildAnswerPayload(),
 * ensuring answer→question association is carried by the payload itself.
 */
export async function submitAnswers(repository, prNumber, answers, answersPayload) {
  // Use the caller-supplied structured payload when available;
  // fall back to building from raw answers map for backwards compatibility.
  const formattedAnswers = answersPayload || Object.keys(answers).map((id) => ({
    question_id: String(id),
    question: "Submitted question",
    category: "general",
    answer: answers[id] || "",
  }));

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/rag/questions/answers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        repository,
        pr_number: Number(prNumber),
        answers: formattedAnswers
      }),
    });
  } catch (err) {
    throw new Error(`Unable to submit answers to ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    let errorDetail = "Failed to submit PR answers.";
    try {
      const errData = await response.json();
      if (errData && errData.detail) {
        errorDetail = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch (_) { }
    throw new Error(errorDetail);
  }

  // Parse and return the real EvaluationDecisionResponse from the backend
  return await response.json();
}

export async function getFinalResult(repository, prNumber) {
  await delay(400);
  const key = getKey(repository, prNumber);
  const pr = MOCK_PRS[key];
  return pr.final_result;
}

/**
 * Step 5: GitHub OAuth Authentication
 */
export async function getAuthUser() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      credentials: "include",
    });
    if (!response.ok) {
      return { authenticated: false };
    }
    return await response.json();
  } catch (err) {
    return { authenticated: false };
  }
}

export async function logoutUser() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: "POST",
      headers: {
        "Accept": "application/json",
      },
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error("Logout failed");
    }
    return await response.json();
  } catch (err) {
    throw err;
  }
}

/**
 * Step 6: Authenticated User Repositories & Pull Requests
 */
export async function getUserRepos() {
  const response = await fetch(`${API_BASE_URL}/api/github/repos`, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Failed to fetch user repositories.");
  }
  return await response.json();
}

export async function getRepoPRs(owner, repo) {
  const response = await fetch(
    `${API_BASE_URL}/api/github/repos/${owner}/${repo}/pulls`,
    {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      credentials: "include",
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch pull requests for ${owner}/${repo}.`);
  }
  return await response.json();
}

export async function getRepoCommits(owner, repo) {
  const response = await fetch(
    `${API_BASE_URL}/api/github/repos/${owner}/${repo}/commits`,
    {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      credentials: "include",
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch commits for ${owner}/${repo}.`);
  }
  return await response.json();
}

export async function analyzeCommit(repository, commitSha) {
  if (!repository || !repository.trim()) {
    throw new Error("Please enter a Repository (e.g., owner/repo).");
  }
  if (!commitSha || !commitSha.trim()) {
    throw new Error("Please select or enter a commit SHA.");
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/commit/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({
        repository: repository.trim(),
        commit_sha: commitSha.trim(),
      }),
    });
  } catch (err) {
    throw new Error(
      `Unable to connect to the backend server at ${API_BASE_URL}. Please verify that FastAPI is running.`
    );
  }

  if (!response.ok) {
    let errorDetail = "An unexpected error occurred while analyzing the commit.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch (_) { }
    if (response.status === 404) {
      errorDetail = `Commit ${commitSha} not found or no longer available in repository '${repository}'.`;
    }
    throw new Error(errorDetail);
  }

  const data = await response.json();

  return {
    pr_id: data.short_sha,
    commit_sha: data.commit_sha,
    short_sha: data.short_sha,
    repository: data.repository,
    title: data.commit_message,
    body: data.commit_message,
    description: data.commit_message,
    state: "committed",
    author: data.author || "GitHub Contributor",
    base_branch: "main",
    head_branch: data.short_sha,
    created_at: new Date().toISOString(),
    files_changed: data.files_changed,
    lines_added: data.lines_added,
    lines_deleted: data.lines_deleted,
    commits: data.commits,
    features: data.features,
    risk_score: data.risk_score,
    risk_level: data.risk_level,
    model_name: data.model_name,
    threshold: 0.5,
    analysis_type: "Commit Risk Analysis",
    changed_files_list: []
  };
}

/**
 * Step 7: Repository Analysis Mode (RAG Codebase Indexing for 0-PR or full-repo analysis)
 */
export async function analyzeRepository(owner, repo, branch = null) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/rag/repository/index`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({ owner, repo, branch }),
    });
  } catch (err) {
    throw new Error(
      `Unable to connect to backend server at ${API_BASE_URL}. Please verify FastAPI is running.`
    );
  }

  if (!response.ok) {
    let errorDetail = "Failed to analyze repository codebase.";
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorDetail = typeof errorData.detail === "string" ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch (_) { }
    throw new Error(errorDetail);
  }

  return await response.json();
}




