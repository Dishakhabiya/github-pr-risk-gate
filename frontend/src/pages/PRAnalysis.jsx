import React from "react";
import PRInput from "../components/PRInput";
import PRStats from "../components/PRStats";
import { GitPullRequest, ArrowRight, User, Calendar, GitBranch, CheckCircle2 } from "lucide-react";

export default function PRAnalysis({ prData, loading, error, onAnalyze, onNext }) {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">PR Ingestion & Preprocessing</h1>
        <p className="page-description">
          Step 1: Enter GitHub repository details to fetch PR metadata, commits, changed files, and unified diff.
        </p>
      </div>

      <PRInput onAnalyze={onAnalyze} loading={loading} error={error} />

      {prData && (
        <div className="pr-overview-card">
          <div className="pr-overview-header">
            <div className="pr-overview-title-box">
              <GitPullRequest size={22} className="text-blue" />
              <div>
                <h3 className="pr-title">{prData.title}</h3>
                <span className="pr-repo">{prData.repository} #{prData.pr_id}</span>
              </div>
            </div>
            <span className="pr-state-badge">{prData.state.toUpperCase()}</span>
          </div>

          <div className="pr-meta-row">
            <div className="meta-pill">
              <User size={14} />
              <span>Author: <strong>{prData.author}</strong></span>
            </div>
            <div className="meta-pill">
              <GitBranch size={14} />
              <span>{prData.base_branch} &larr; {prData.head_branch}</span>
            </div>
            <div className="meta-pill">
              <Calendar size={14} />
              <span>{new Date(prData.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          <div className="pr-body-box">
            <h4 className="body-label">PR Description:</h4>
            <p className="body-text">{prData.body}</p>
          </div>

          <PRStats features={prData.features} />

          {prData.changed_files_list && prData.changed_files_list.length > 0 && (
            <div className="files-table-section">
              <h4 className="body-label">Changed Files ({prData.changed_files_list.length}):</h4>
              <div className="files-list">
                {prData.changed_files_list.map((file, idx) => (
                  <div key={idx} className="file-row">
                    <span className="file-name">{file.filename}</span>
                    <div className="file-meta-right">
                      <span className="file-status">{file.status}</span>
                      <span className="file-add">+ {file.additions}</span>
                      <span className="file-del">- {file.deletions}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="page-action-row">
            <div className="ingestion-success">
              <CheckCircle2 size={18} className="text-green" />
              <span>PR metadata and diff successfully ingested!</span>
            </div>
            <button onClick={onNext} className="btn-primary">
              <span>Proceed to Risk Analysis</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
