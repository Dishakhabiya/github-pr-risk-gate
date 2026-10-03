import React from "react";
import { CheckCircle2, XCircle, ExternalLink, ShieldCheck, Award, ListChecks } from "lucide-react";

export default function DecisionCard({ finalResult }) {
  if (!finalResult) return null;

  const isPass = finalResult.decision === "PASS";
  const understandingPct = (finalResult.understanding_score * 100).toFixed(0);
  const riskPct = (finalResult.risk_score * 100).toFixed(1);

  return (
    <div className={`decision-card ${isPass ? "decision-pass" : "decision-block"}`}>
      <div className="decision-header">
        <div className="decision-title-group">
          {isPass ? (
            <CheckCircle2 size={36} className="text-green" />
          ) : (
            <XCircle size={36} className="text-red" />
          )}
          <div>
            <h2 className="decision-title">Final Merge Gate Decision</h2>
            <p className="decision-subtitle">Person 3 LLM Understanding Evaluation Output</p>
          </div>
        </div>

        <div className={`decision-badge ${isPass ? "badge-pass" : "badge-block"}`}>
          {finalResult.decision}
        </div>
      </div>

      <div className="metrics-row">
        <div className="metric-box">
          <Award size={20} className="text-purple" />
          <div>
            <span className="metric-val">{understandingPct}%</span>
            <span className="metric-lbl">Understanding Score</span>
          </div>
        </div>

        <div className="metric-box">
          <ShieldCheck size={20} className={finalResult.risk_level === "HIGH" ? "text-red" : "text-green"} />
          <div>
            <span className="metric-val">{riskPct}% ({finalResult.risk_level})</span>
            <span className="metric-lbl">ML Risk Score</span>
          </div>
        </div>
      </div>

      <div className="reasons-box">
        <div className="reasons-header">
          <ListChecks size={18} />
          <span>Evaluation Rationale & Findings</span>
        </div>
        <ul className="reasons-list">
          {finalResult.reasons.map((reason, idx) => (
            <li key={idx} className="reason-item">
              <span className="reason-bullet">•</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      {finalResult.github_pr_url && (
        <div className="pr-link-box">
          <a
            href={finalResult.github_pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="github-pr-link"
          >
            <span>View Pull Request on GitHub</span>
            <ExternalLink size={16} />
          </a>
        </div>
      )}
    </div>
  );
}
