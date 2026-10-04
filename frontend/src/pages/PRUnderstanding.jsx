import React from "react";
import RepositoryContext from "../components/RepositoryContext";
import QuestionCard from "../components/QuestionCard";
import { BookOpen } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const GithubIcon = ({ size = 16 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
    />
  </svg>
);

export default function PRUnderstanding({
  contextData,
  questionData,
  answers,
  onAnswerChange,
  onSubmitAnswers,
  submitting,
  submitError,
  submitSuccess,
  authUser,
  currentPR,
}) {
  if (authUser && !authUser.authenticated) {
    const loginUrl = `${API_BASE_URL}/api/auth/github/login`;
    return (
      <div className="page-container">
        <div className="empty-state-card">
          <BookOpen size={40} className="text-muted" />
          <h3>Please sign in with GitHub to continue.</h3>
          <p>Sign in with GitHub to access repository context and PR understanding questions.</p>
          <div style={{ marginTop: "1rem" }}>
            <a href={loginUrl} className="btn-github-login" style={{ display: "inline-flex" }}>
              <GithubIcon size={16} />
              <span>Login with GitHub</span>
            </a>
          </div>
        </div>
      </div>
    );
  }

  if (!contextData && !questionData) {
    return (
      <div className="page-container">
        <div className="empty-state-card">
          <BookOpen size={40} className="text-muted" />
          {currentPR ? (
            <>
              <h3>Loading Repository Context...</h3>
              <p>Fetching context and generating questions for <strong>{currentPR.repository}#{currentPR.pr_id}</strong>...</p>
            </>
          ) : (
            <>
              <h3>No Repository Context Loaded</h3>
              <p>Please analyze a PR in the <strong>PR Analysis</strong> tab first.</p>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">RAG Context &amp; PR Questions (Person 2)</h1>
        <p className="page-description">
          Step 3: Review retrieved repository code context and provide technical explanations to PR comprehension questions.
        </p>
      </div>

      <RepositoryContext contextList={contextData?.repository_context || []} />

      <QuestionCard
        questions={questionData?.questions || []}
        answers={answers}
        onAnswerChange={onAnswerChange}
        onSubmitAnswers={onSubmitAnswers}
        submitting={submitting}
        submitError={submitError}
        submitSuccess={submitSuccess}
      />
    </div>
  );
}
