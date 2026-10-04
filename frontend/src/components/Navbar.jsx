import React from "react";
import { GitPullRequest, ShieldAlert, BookOpen, CheckCircle, Cpu, LogOut } from "lucide-react";

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

export default function Navbar({ activeTab, setActiveTab, currentPR, authUser, onLogout }) {

  const tabs = [
    { id: "analysis", label: "1. PR Analysis", icon: GitPullRequest },
    { id: "risk", label: "2. Risk Analysis", icon: ShieldAlert },
    { id: "understanding", label: "3. PR Understanding", icon: BookOpen },
    { id: "result", label: "4. Final Result", icon: CheckCircle },
  ];

  const loginUrl = `${API_BASE_URL}/api/auth/github/login`;

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

        <div className="navbar-right">
          {currentPR && (
            <div className="active-pr-badge">
              <GitPullRequest size={14} />
              <span>{currentPR.repository}#{currentPR.pr_id}</span>
              <span className={`pill-badge ${currentPR.risk_analysis?.risk_level === "HIGH" ? "badge-high" : "badge-low"}`}>
                {currentPR.risk_analysis?.risk_level} RISK
              </span>
            </div>
          )}

          {authUser?.authenticated ? (
            <div className="user-profile-badge">
              {authUser.avatar_url ? (
                <img src={authUser.avatar_url} alt={authUser.login} className="user-avatar" />
              ) : (
                <div className="user-avatar-placeholder">{authUser.login?.[0]?.toUpperCase()}</div>
              )}
              <span className="user-login">{authUser.login}</span>
              <button onClick={onLogout} className="btn-logout" title="Logout">
                <LogOut size={14} />
                <span>Logout</span>
              </button>
            </div>
          ) : (
            <a
              href={loginUrl}
              className="btn-github-login"
            >
              <GithubIcon size={16} />
              <span>Login with GitHub</span>
            </a>
          )}

        </div>
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

