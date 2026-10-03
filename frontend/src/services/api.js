/**
 * Mock API Layer for GitHub PR Risk Gate & Understanding System.
 * Modular service layer simulating responses for Person 1 (ML Risk), Person 2 (RAG), and Person 3 (LLM Decision).
 * Easily replaceable with real FastAPI endpoints in production.
 */

import { MOCK_PRS, DEFAULT_PR_KEY } from "../mock/mockData";

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
 * Step 1: Ingest and Analyze PR metadata
 */
export async function analyzePR(repository, prNumber) {
  await delay(600);

  if (!repository || !prNumber) {
    throw new Error("Please enter both Repository (e.g., kubernetes/kubernetes) and PR Number.");
  }

  const key = getKey(repository, prNumber);
  const pr = MOCK_PRS[key];

  if (!pr) {
    throw new Error(`Pull Request #${prNumber} in '${repository}' was not found.`);
  }

  return {
    pr_id: pr.pr_id,
    repository: pr.repository,
    title: pr.title,
    body: pr.body,
    state: pr.state,
    author: pr.author,
    base_branch: pr.base_branch,
    head_branch: pr.head_branch,
    created_at: pr.created_at,
    features: pr.features,
    changed_files_list: pr.changed_files_list
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

export async function getQuestions(repository, prNumber) {
  await delay(300);
  const key = getKey(repository, prNumber);
  const pr = MOCK_PRS[key];
  return {
    questions: pr.questions,
    sample_answers: pr.sample_answers
  };
}

/**
 * Step 4: Submit Developer Answers & Obtain Person 3 Final LLM Evaluation
 */
export async function submitAnswers(repository, prNumber, answers) {
  await delay(700);

  const key = getKey(repository, prNumber);
  const pr = MOCK_PRS[key];

  // Simple heuristic calculation based on answers completeness for mock demo
  const filledCount = Object.values(answers || {}).filter((a) => a && a.trim().length > 10).length;
  const totalQuestions = pr.questions.length;
  
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
    pr_id: pr.pr_id,
    repository: pr.repository,
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
