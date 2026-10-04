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
  try {
    // Generate questions for this PR using US-11 endpoint
    response = await fetch(`${API_BASE_URL}/api/rag/pr/questions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        pr_info: {
          repository: prData.repository,
          title: prData.title || `PR ${prData.pr_id}`,
          description: prData.body || prData.description || "",
          changed_files: prData.files_changed || []
        },
        num_questions: 3
      }),
    });
  } catch (err) {
    throw new Error(`Unable to fetch questions from ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw new Error("Failed to generate PR questions.");
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
    throw new Error("Failed to submit PR answers.");
  }

  // To preserve frontend behavior (which expects final result from submitAnswers), 
  // we combine the real submission with a mock final result.
  const key = getKey(repository, prNumber);
  const pr = MOCK_PRS[key] || MOCK_PRS[DEFAULT_PR_KEY];

  const filledCount = Object.values(answers || {}).filter((a) => a && a.trim().length > 10).length;
  const totalQuestions = Object.keys(answers).length || 3;
  
  let score = pr.final_result.understanding_score;
  let decision = pr.final_result.decision;
  let reasons = [...pr.final_result.reasons];

  if (filledCount === 0) {
    score = 0.20;
    decision = "BLOCK";
    reasons = [
      "Developer provided no answers to PR understanding questions.",
      "Unable to verify developer comprehension of security or architectural changes."
    ];
  } else if (filledCount < totalQuestions) {
    score = 0.65;
    decision = pr.risk_analysis.risk_level === "HIGH" ? "BLOCK" : "PASS";
    reasons = [
      `Developer answered ${filledCount} of ${totalQuestions} questions.`,
      "Partial understanding demonstrated; high risk PR requires complete answers."
    ];
  }

  return {
    pr_id: prNumber,
    repository: repository,
    risk_score: pr.risk_analysis.risk_score,
    risk_level: pr.risk_analysis.risk_level,
    understanding_score: score,
    decision: decision,
    reasons: reasons,
    github_pr_url: pr.final_result.github_pr_url
  };
}

export async function getFinalResult(repository, prNumber) {
  await delay(400);
  const key = getKey(repository, prNumber);
  const pr = MOCK_PRS[key];
  return pr.final_result;
}
