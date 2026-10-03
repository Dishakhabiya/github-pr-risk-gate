import React from "react";
import { HelpCircle, Sparkles, Send, RefreshCw } from "lucide-react";

export default function QuestionCard({
  questions,
  answers,
  onAnswerChange,
  onPrefillSampleAnswers,
  onSubmitAnswers,
  submitting,
}) {
  if (!questions || questions.length === 0) return null;

  return (
    <div className="card-container">
      <div className="card-header-flex">
        <div className="card-header-left">
          <div className="card-header-icon text-purple">
            <HelpCircle size={20} />
          </div>
          <div>
            <h2 className="card-title">PR Understanding Questions</h2>
            <p className="card-description">
              Questions generated from RAG context to evaluate developer comprehension of PR changes.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onPrefillSampleAnswers}
          className="btn-secondary"
          title="Fill sample developer answers for demo"
        >
          <Sparkles size={16} />
          <span>Prefill Demo Answers</span>
        </button>
      </div>

      <div className="questions-list">
        {questions.map((q, idx) => (
          <div key={q.id} className="question-item">
            <label htmlFor={`q-input-${q.id}`} className="question-label">
              <span className="question-number">Q{idx + 1}.</span> {q.question}
            </label>
            <textarea
              id={`q-input-${q.id}`}
              className="text-area-input"
              rows={3}
              placeholder={q.placeholder || "Enter your technical explanation..."}
              value={answers[q.id] || ""}
              onChange={(e) => onAnswerChange(q.id, e.target.value)}
            />
          </div>
        ))}
      </div>

      <div className="submit-section">
        <button
          type="button"
          onClick={onSubmitAnswers}
          disabled={submitting}
          className="btn-primary"
        >
          {submitting ? (
            <>
              <RefreshCw className="spin-icon" size={18} />
              <span>Evaluating Answers via LLM...</span>
            </>
          ) : (
            <>
              <Send size={18} />
              <span>Submit Answers for LLM Evaluation</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
