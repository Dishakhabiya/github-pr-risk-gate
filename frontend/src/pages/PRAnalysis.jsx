import React from "react";
import PRInput from "../components/PRInput";
import PRStats from "../components/PRStats";
import { GitPullRequest, GitCommit, ArrowRight, User, Calendar, GitBranch, CheckCircle2, FolderGit2, Layers, Database } from "lucide-react";

export default function PRAnalysis({ prData, repoData, loading, error, onAnalyze, onAnalyzeCommit, onAnalyzeRepo, onNext, authUser }) {
  const isCommitAnalysis = prData?.analysis_type === "Commit Risk Analysis";

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">PR & Commit Risk Analysis</h1>
        <p className="page-description">
          Step 1: Select a Pull Request or analyze a commit for creation-time ML risk prediction.
        </p>
      </div>

      <PRInput
        onAnalyze={onAnalyze}
        onAnalyzeCommit={onAnalyzeCommit}
        onAnalyzeRepo={onAnalyzeRepo}
        loading={loading}
        error={error}
        authUser={authUser}
      />

      {/* Overview Card for PR or Commit */}
      {prData && (
        <div className="pr-overview-card">
          <div className="pr-overview-header">
            <div className="pr-overview-title-box">
              {isCommitAnalysis ? (
                <GitCommit size={22} className="text-blue" />
              ) : (
                <GitPullRequest size={22} className="text-blue" />
              )}
              <div>
                <h3 className="pr-title">{prData.title}</h3>
                <span className="pr-repo">
                  {prData.repository} {isCommitAnalysis ? `@ ${prData.short_sha || prData.pr_id}` : `#${prData.pr_id}`}
                </span>
              </div>
            </div>
            <span className="pr-state-badge">
              {isCommitAnalysis ? "COMMIT RISK ANALYSIS" : prData.state.toUpperCase()}
            </span>
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
            <h4 className="body-label">{isCommitAnalysis ? "Commit Message:" : "PR Description:"}</h4>
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
              <span>{isCommitAnalysis ? "Commit diff and features successfully analyzed!" : "PR metadata and diff successfully ingested!"}</span>
            </div>
            <button onClick={onNext} className="btn-primary">
              <span>Proceed to Risk Analysis</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Repository Analysis (RAG Ingestion) Card */}
      {repoData && !prData && (
        <div className="pr-overview-card">
          <div className="pr-overview-header">
            <div className="pr-overview-title-box">
              <FolderGit2 size={22} className="text-purple" style={{ color: "#8b5cf6" }} />
              <div>
                <h3 className="pr-title">Repository Codebase Indexing</h3>
                <span className="pr-repo">{repoData.repository}</span>
              </div>
            </div>
            <span className="pr-state-badge" style={{ backgroundColor: "rgba(139, 92, 246, 0.2)", color: "#a78bfa" }}>
              CODEBASE INDEXED
            </span>
          </div>

          <div className="pr-body-box" style={{ marginTop: "1rem" }}>
            <h4 className="body-label">Indexing Result:</h4>
            <p className="body-text">{repoData.message}</p>
          </div>

          <div className="stats-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginTop: "1rem" }}>
            <div className="stat-card">
              <div className="stat-icon-wrapper text-blue">
                <FolderGit2 size={18} />
              </div>
              <div>
                <span className="stat-label">Source Documents</span>
                <span className="stat-value">{repoData.documents_count}</span>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon-wrapper text-purple" style={{ color: "#8b5cf6" }}>
                <Layers size={18} />
              </div>
              <div>
                <span className="stat-label">RAG Code Chunks</span>
                <span className="stat-value">{repoData.chunks_stored}</span>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon-wrapper text-green">
                <Database size={18} />
              </div>
              <div>
                <span className="stat-label">Vector Store</span>
                <span className="stat-value">Ready</span>
              </div>
            </div>
          </div>

          <div className="page-action-row" style={{ marginTop: "1.5rem" }}>
            <div className="ingestion-success">
              <CheckCircle2 size={18} className="text-green" />
              <span>Repository codebase successfully indexed into Vector DB for RAG retrieval!</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
