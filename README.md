# github-pr-risk-gate
AI-powered GitHub Pull Request analysis system that combines **Machine Learning, RAG, LLMs, and MLOps** to assess PR risk, evaluate developer understanding, and provide a PASS/BLOCK merge recommendation.

## 🚀 Overview

GitHub PR Risk Gate analyzes a Pull Request and the relevant repository code to determine:

- How risky the PR is
- Which parts of the repository are relevant to the changes
- Whether the developer understands the changes
- Whether the PR should PASS or be BLOCKED based on configured thresholds

The system retrieves repository context using **RAG (Retrieval-Augmented Generation)** and uses an **LLM** to evaluate developer answers about the PR.

The final analysis can be automatically posted back to the GitHub Pull Request.

---

## 🔄 System Workflow

```text
Developer
    │
    ▼
GitHub Repository
    │
    ▼
Select Pull Request
    │
    ▼
┌─────────────────────────┐
│ PR Ingestion &          │
│ Preprocessing            │
└────────────┬────────────┘
             │
             ▼
     PR Feature Extraction
             │
             ▼
     ML Risk Prediction
             │
             ▼
        Risk Score
             │
             ├─────────────────────┐
             │                     │
             ▼                     ▼
     Repository Ingestion      PR Information
             │                     │
             ▼                     │
       Code Chunking              │
             │                     │
             ▼                     │
        Embeddings                │
             │                     │
             ▼                     │
        Vector DB                 │
             │                     │
             ▼                     │
   Relevant Repository Context ◄──┘
             │
             ▼
   PR-Specific Questions
             │
             ▼
      Developer Answers
             │
             ▼
       LLM Evaluation
             │
             ▼
    Understanding Score
             │
             ▼
       PASS / BLOCK
             │
             ▼
      GitHub PR Comment
