import React from "react";
import RepositoryContext from "../components/RepositoryContext";
import QuestionCard from "../components/QuestionCard";
import { BookOpen } from "lucide-react";

export default function PRUnderstanding({
  contextData,
  questionData,
  answers,
  onAnswerChange,
  onSubmitAnswers,
  submitting,
  submitError,
  submitSuccess,
}) {
  if (!contextData && !questionData) {
    return (
      <div className="page-container">
        <div className="empty-state-card">
          <BookOpen size={40} className="text-muted" />
          <h3>No Repository Context Loaded</h3>
          <p>Please analyze a PR in the <strong>PR Analysis</strong> tab first.</p>
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
