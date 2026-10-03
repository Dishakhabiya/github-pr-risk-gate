import React from "react";
import DecisionCard from "../components/DecisionCard";
import { CheckCircle, RotateCcw } from "lucide-react";

export default function FinalResult({ finalResult, onReset }) {
  if (!finalResult) {
    return (
      <div className="page-container">
        <div className="empty-state-card">
          <CheckCircle size={40} className="text-muted" />
          <h3>No Decision Evaluated Yet</h3>
          <p>Please submit answers in the <strong>PR Understanding</strong> tab to view the final LLM evaluation and merge decision.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">LLM Evaluation & Merge Decision (Person 3)</h1>
        <p className="page-description">
          Step 4: Comprehensive LLM evaluation synthesizing ML Risk Score and Developer Understanding Score into a final PASS/BLOCK merge decision.
        </p>
      </div>

      <DecisionCard finalResult={finalResult} />

      <div className="page-action-row center-align">
        <button onClick={onReset} className="btn-secondary">
          <RotateCcw size={18} />
          <span>Analyze Another Pull Request</span>
        </button>
      </div>
    </div>
  );
}
