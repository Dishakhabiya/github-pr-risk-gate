import React from "react";
import RiskCard from "../components/RiskCard";
import PRStats from "../components/PRStats";
import { ArrowRight, Cpu, Layers } from "lucide-react";

export default function RiskAnalysis({ riskData, prData, onNext }) {
  if (!riskData) {
    return (
      <div className="page-container">
        <div className="empty-state-card">
          <Cpu size={40} className="text-muted" />
          <h3>No Risk Data Loaded</h3>
          <p>Please enter a PR number in the <strong>PR Analysis</strong> section first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">ML Risk Prediction (Person 1)</h1>
        <p className="page-description">
          Step 2: Evaluates creation-time features using the trained Logistic Regression ML risk model artifact.
        </p>
      </div>

      <RiskCard riskAnalysis={riskData} />

      <PRStats features={riskData.features || prData?.features} />

      <div className="pipeline-info-card">
        <div className="pipeline-info-header">
          <Layers size={20} className="text-blue" />
          <h3>Feature Leakage Prevention Safeguard</h3>
        </div>
        <p className="pipeline-info-text">
          Our ML model uses <strong>ONLY creation-time features</strong> (code churn, additions/deletions ratio, source/test file counts). Post-creation review outcomes are strictly excluded to eliminate data leakage.
        </p>
      </div>

      <div className="page-action-row right-align">
        <button onClick={onNext} className="btn-primary">
          <span>Proceed to PR Understanding</span>
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}
