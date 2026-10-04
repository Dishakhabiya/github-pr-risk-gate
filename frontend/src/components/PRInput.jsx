import React, { useState, useEffect } from "react";
import { Search, Sparkles, AlertCircle, RefreshCw, FolderGit2, GitPullRequest, GitCommit, Info } from "lucide-react";
import { getUserRepos, getRepoPRs, getRepoCommits } from "../services/api";

export default function PRInput({ onAnalyze, onAnalyzeCommit, onAnalyzeRepo, loading, error, authUser }) {
  const [repo, setRepo] = useState("");
  const [prNumber, setPrNumber] = useState("");
  const [userRepos, setUserRepos] = useState([]);
  const [repoPRs, setRepoPRs] = useState([]);
  const [repoCommits, setRepoCommits] = useState([]);
  const [selectedCommitSha, setSelectedCommitSha] = useState("");
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [loadingPRs, setLoadingPRs] = useState(false);
  const [loadingCommits, setLoadingCommits] = useState(false);
  const [fetchError, setFetchError] = useState(null);
  const [manualMode, setManualMode] = useState(false);

  const presets = [
    { repo: "kubernetes/kubernetes", pr: "142645", label: "K8s (Low Risk)" },
    { repo: "tensorflow/tensorflow", pr: "128355", label: "TensorFlow (High Risk)" },
    { repo: "microsoft/vscode", pr: "339476", label: "VSCode (Low Risk)" },
  ];

  // Fetch repositories when user is authenticated
  useEffect(() => {
    if (authUser?.authenticated) {
      loadRepositories();
    } else {
      setUserRepos([]);
      setRepoPRs([]);
      setRepoCommits([]);
      setSelectedCommitSha("");
      setRepo("kubernetes/kubernetes");
      setPrNumber("142645");
      setManualMode(false);
    }
  }, [authUser?.authenticated]);

  const loadRepositories = async () => {
    setLoadingRepos(true);
    setFetchError(null);
    try {
      const repos = await getUserRepos();
      setUserRepos(repos);
      if (repos && repos.length > 0) {
        const firstRepo = repos[0].full_name;
        setRepo(firstRepo);
        loadPullRequests(firstRepo);
      } else {
        setRepo("");
        setPrNumber("");
      }
    } catch (err) {
      setFetchError(err.message || "Failed to load user repositories.");
    } finally {
      setLoadingRepos(false);
    }
  };

  const loadPullRequests = async (fullRepoName) => {
    if (!fullRepoName || !fullRepoName.includes("/")) return;
    setLoadingPRs(true);
    setFetchError(null);
    const [owner, repoName] = fullRepoName.split("/");
    try {
      const pulls = await getRepoPRs(owner, repoName);
      setRepoPRs(pulls);
      if (pulls && pulls.length > 0) {
        setPrNumber(String(pulls[0].number));
        setRepoCommits([]);
        setSelectedCommitSha("");
      } else {
        setPrNumber("");
        loadCommits(fullRepoName);
      }
    } catch (err) {
      setRepoPRs([]);
      setPrNumber("");
      setRepoCommits([]);
      setSelectedCommitSha("");
      setFetchError(err.message || `Repository '${fullRepoName}' not found or access denied.`);
    } finally {
      setLoadingPRs(false);
    }
  };

  const loadCommits = async (fullRepoName) => {
    if (!fullRepoName || !fullRepoName.includes("/")) return;
    setLoadingCommits(true);
    const [owner, repoName] = fullRepoName.split("/");
    try {
      const commits = await getRepoCommits(owner, repoName);
      setRepoCommits(commits || []);
      setSelectedCommitSha("");
    } catch (err) {
      setRepoCommits([]);
      setSelectedCommitSha("");
    } finally {
      setLoadingCommits(false);
    }
  };

  const handleRepoChange = (e) => {
    const selected = e.target.value;
    setRepo(selected);
    setPrNumber("");
    setSelectedCommitSha("");
    setRepoCommits([]);
    loadPullRequests(selected);
  };

  const handlePRChange = (e) => {
    setPrNumber(e.target.value);
  };

  const handleCommitChange = (e) => {
    setSelectedCommitSha(e.target.value);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!repo) return;

    const isZeroPRRepo = authUser?.authenticated && userRepos.length > 0 && !manualMode && repoPRs.length === 0;

    if (isZeroPRRepo) {
      if (!selectedCommitSha) return;
      if (onAnalyzeCommit) onAnalyzeCommit(repo, selectedCommitSha);
    } else {
      if (!prNumber) return;
      onAnalyze(repo, prNumber);
    }
  };

  const handleSelectPreset = (preset) => {
    setRepo(preset.repo);
    setPrNumber(preset.pr);
    onAnalyze(preset.repo, preset.pr);
  };

  const isZeroPRMode = authUser?.authenticated && userRepos.length > 0 && !manualMode && repoPRs.length === 0;

  return (
    <div className="card-container">
      <div className="card-header">
        <div className="card-header-icon">
          <Search size={20} />
        </div>
        <div>
          <h2 className="card-title">Select Pull Request or Commit</h2>
          <p className="card-description">
            {authUser?.authenticated
              ? `Select from your GitHub repositories (${authUser.login}). Repositories without PRs can analyze commits.`
              : "Enter a GitHub repository path and PR number or log in to select your own repositories."}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="form-layout">
        {authUser?.authenticated && userRepos.length > 0 && !manualMode ? (
          <>
            <div className="input-group">
              <label htmlFor="repo-select" className="input-label">
                <FolderGit2 size={14} style={{ display: "inline", marginRight: 6 }} />
                Your Repositories ({userRepos.length})
              </label>

              {loadingRepos ? (
                <div className="select-loading">Loading repositories...</div>
              ) : (
                <select
                  id="repo-select"
                  className="text-input"
                  value={repo}
                  onChange={handleRepoChange}
                  required
                >
                  {userRepos.map((r) => (
                    <option key={r.full_name} value={r.full_name}>
                      {r.full_name} {r.private ? "(Private)" : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="input-group">
              <label htmlFor="pr-select" className="input-label">
                <GitPullRequest size={14} style={{ display: "inline", marginRight: 6 }} />
                Pull Request
              </label>

              {loadingPRs ? (
                <div className="select-loading">Loading pull requests...</div>
              ) : repoPRs.length > 0 ? (
                <select
                  id="pr-select"
                  className="text-input"
                  value={prNumber}
                  onChange={handlePRChange}
                  required
                >
                  {repoPRs.map((p) => (
                    <option key={p.number} value={p.number}>
                      #{p.number} - {p.title} ({p.state})
                    </option>
                  ))}
                </select>
              ) : (
                <div className="no-prs-notice" style={{ padding: "0.75rem", backgroundColor: "rgba(59, 130, 246, 0.1)", borderRadius: "8px", border: "1px solid rgba(59, 130, 246, 0.2)", color: "#93c5fd", display: "flex", alignItems: "center", gap: "8px", fontSize: "0.9rem" }}>
                  <Info size={16} />
                  <span>No pull requests found in this repository. You can optionally analyze a commit instead.</span>
                </div>
              )}
            </div>

            {repoPRs.length === 0 && !loadingPRs && (
              <div className="input-group" style={{ marginTop: "0.75rem" }}>
                <label htmlFor="commit-select" className="input-label">
                  <GitCommit size={14} style={{ display: "inline", marginRight: 6 }} />
                  Commit (Optional)
                </label>

                {loadingCommits ? (
                  <div className="select-loading">Loading commits...</div>
                ) : (
                  <select
                    id="commit-select"
                    className="text-input"
                    value={selectedCommitSha}
                    onChange={handleCommitChange}
                  >
                    <option value="">-- Select a commit --</option>
                    {repoCommits.map((c) => (
                      <option key={c.sha} value={c.sha}>
                        {c.short_sha} - {c.message} ({c.author?.login || c.author?.name || "unknown"})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </>
        ) : (
          <>
            <div className="input-group">
              <label htmlFor="repo-input" className="input-label">
                GitHub Repository
              </label>
              <input
                id="repo-input"
                type="text"
                className="text-input"
                placeholder="e.g. kubernetes/kubernetes"
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                required
              />
            </div>

            <div className="input-group">
              <label htmlFor="pr-input" className="input-label">
                PR Number
              </label>
              <input
                id="pr-input"
                type="number"
                className="text-input"
                placeholder="e.g. 123"
                value={prNumber}
                onChange={(e) => setPrNumber(e.target.value)}
                required
              />
            </div>
          </>
        )}

        <div className="input-actions-row">
          {authUser?.authenticated && userRepos.length > 0 && (
            <button
              type="button"
              className="btn-mode-toggle"
              onClick={() => setManualMode(!manualMode)}
            >
              {manualMode ? "Use Dropdown Selection" : "Enter Path Manually"}
            </button>
          )}

          <button
            type="submit"
            disabled={loading || !repo || (isZeroPRMode && !selectedCommitSha) || (!isZeroPRMode && !prNumber)}
            className="btn-primary"
          >
            {loading ? (
              <>
                <RefreshCw className="spin-icon" size={18} />
                <span>{isZeroPRMode ? "Analyzing Commit..." : "Analyzing PR..."}</span>
              </>
            ) : isZeroPRMode ? (
              <>
                <GitCommit size={18} />
                <span>Analyze Commit</span>
              </>
            ) : (
              <>
                <Sparkles size={18} />
                <span>Analyze PR</span>
              </>
            )}
          </button>
        </div>
      </form>

      {(error || fetchError) && (
        <div className="error-box">
          <AlertCircle size={18} />
          <span>{error || fetchError}</span>
        </div>
      )}

      {!authUser?.authenticated && (
        <div className="preset-section">
          <span className="preset-title">Quick Demo Presets:</span>
          <div className="preset-buttons">
            {presets.map((preset) => (
              <button
                key={preset.pr}
                type="button"
                onClick={() => handleSelectPreset(preset)}
                className="preset-btn"
              >
                {preset.label} (#{preset.pr})
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
