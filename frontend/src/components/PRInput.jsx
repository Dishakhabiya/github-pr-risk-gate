import React, { useState } from "react";
import { Search, Sparkles, AlertCircle, RefreshCw } from "lucide-react";

export default function PRInput({ onAnalyze, loading, error }) {
  const [repo, setRepo] = useState("kubernetes/kubernetes");
  const [prNumber, setPrNumber] = useState("142645");

  const presets = [
    { repo: "kubernetes/kubernetes", pr: "142645", label: "K8s (Low Risk)" },
    { repo: "tensorflow/tensorflow", pr: "128355", label: "TensorFlow (High Risk)" },
    { repo: "microsoft/vscode", pr: "339476", label: "VSCode (Low Risk)" },
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    onAnalyze(repo, prNumber);
  };

  const handleSelectPreset = (preset) => {
    setRepo(preset.repo);
    setPrNumber(preset.pr);
    onAnalyze(preset.repo, preset.pr);
  };

  return (
    <div className="card-container">
      <div className="card-header">
        <div className="card-header-icon">
          <Search size={20} />
        </div>
        <div>
          <h2 className="card-title">Select Pull Request</h2>
          <p className="card-description">
            Enter a GitHub repository path and PR number to trigger the ingestion and risk gating pipeline.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="form-layout">
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

        <button
          type="submit"
          disabled={loading}
          className="btn-primary"
        >
          {loading ? (
            <>
              <RefreshCw className="spin-icon" size={18} />
              <span>Analyzing PR...</span>
            </>
          ) : (
            <>
              <Sparkles size={18} />
              <span>Analyze PR</span>
            </>
          )}
        </button>
      </form>

      {error && (
        <div className="error-box">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

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
    </div>
  );
}
