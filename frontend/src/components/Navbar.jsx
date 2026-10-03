import React from "react";
import { GitPullRequest, ShieldAlert, BookOpen, CheckCircle, Cpu } from "lucide-react";

export default function Navbar({ activeTab, setActiveTab, currentPR }) {
  const tabs = [
    { id: "analysis", label: "1. PR Analysis", icon: GitPullRequest },
    { id: "risk", label: "2. Risk Analysis", icon: ShieldAlert },
    { id: "understanding", label: "3. PR Understanding", icon: BookOpen },
    { id: "result", label: "4. Final Result", icon: CheckCircle },
  ];

  return (
    <header className="navbar-container">
      <div className="navbar-inner">
        <div className="brand-section">
          <div className="brand-icon">
            <Cpu size={24} />
          </div>
          <div>
            <h1 className="brand-title">GitHub PR Risk Gate</h1>
            <p className="brand-subtitle">AI-Powered Risk Assessment & Merge Gating</p>
          </div>
        </div>

        {currentPR && (
          <div className="active-pr-badge">
            <GitPullRequest size={14} />
            <span>{currentPR.repository}#{currentPR.pr_id}</span>
            <span className={`pill-badge ${currentPR.risk_analysis?.risk_level === "HIGH" ? "badge-high" : "badge-low"}`}>
              {currentPR.risk_analysis?.risk_level} RISK
            </span>
          </div>
        )}
      </div>

      <nav className="tab-navigation">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`nav-tab ${isActive ? "nav-tab-active" : ""}`}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
    </header>
  );
}
