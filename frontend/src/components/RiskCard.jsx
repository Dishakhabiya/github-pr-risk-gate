import React from "react";
import { ShieldAlert, ShieldCheck, Cpu, Sliders } from "lucide-react";

export default function RiskCard({ riskAnalysis }) {
  if (!riskAnalysis) return null;

  const isHigh = riskAnalysis.risk_level === "HIGH";
  const percentage = (riskAnalysis.risk_score * 100).toFixed(1);

  return (
    <div className={`risk-card ${isHigh ? "risk-card-high" : "risk-card-low"}`}>
      <div className="risk-card-header">
        <div className="risk-title-box">
          {isHigh ? <ShieldAlert size={28} className="text-red" /> : <ShieldCheck size={28} className="text-green" />}
          <div>
            <h2 className="risk-header-title">ML Risk Assessment</h2>
            <p className="risk-header-subtitle">Person 1 ML Risk Prediction Model Output</p>
          </div>
        </div>
        <div className={`risk-level-badge ${isHigh ? "badge-high" : "badge-low"}`}>
          {riskAnalysis.risk_level} RISK
        </div>
      </div>

      <div className="risk-gauge-box">
        <div className="gauge-metric">
          <span className="gauge-number">{percentage}%</span>
          <span className="gauge-label">Risk Score (Probability)</span>
        </div>
        <div className="gauge-bar-background">
          <div
            className={`gauge-bar-fill ${isHigh ? "fill-high" : "fill-low"}`}
            style={{ width: `${Math.min(100, Math.max(5, percentage))}%` }}
          ></div>
        </div>
      </div>

      <div className="risk-metadata-grid">
        <div className="meta-item">
          <Cpu size={16} />
          <span>Model Architecture: <strong>{riskAnalysis.model_name}</strong></span>
        </div>
        <div className="meta-item">
          <Sliders size={16} />
          <span>Decision Threshold: <strong>{riskAnalysis.threshold}</strong></span>
        </div>
      </div>
    </div>
  );
}
