import React from "react";
import { Files, PlusCircle, MinusCircle, GitCommit, Ratio, FileCode } from "lucide-react";

export default function PRStats({ features }) {
  if (!features) return null;

  const stats = [
    { label: "Files Changed", value: features.files_changed, icon: Files, color: "text-blue" },
    { label: "Lines Added", value: `+${features.lines_added}`, icon: PlusCircle, color: "text-green" },
    { label: "Lines Deleted", value: `-${features.lines_deleted}`, icon: MinusCircle, color: "text-red" },
    { label: "Total Churn", value: features.total_lines_changed, icon: FileCode, color: "text-purple" },
    { label: "Commits", value: features.commits_count, icon: GitCommit, color: "text-amber" },
    { label: "Additions/Deletions Ratio", value: features.additions_to_deletions_ratio, icon: Ratio, color: "text-teal" },
  ];

  return (
    <div className="stats-section">
      <h3 className="section-title">Creation-Time Code Statistics</h3>
      <div className="stats-grid">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="stat-card">
              <div className="stat-header">
                <span className="stat-label">{stat.label}</span>
                <Icon size={18} className={stat.color} />
              </div>
              <div className="stat-value">{stat.value}</div>
            </div>
          );
        })}
      </div>

      <div className="category-badges">
        <span className="badge-item">Source Files: <strong>{features.source_files_changed}</strong></span>
        <span className="badge-item">Test Files: <strong>{features.test_files_changed}</strong></span>
        <span className="badge-item">Doc Files: <strong>{features.documentation_files_changed}</strong></span>
        <span className="badge-item">Config Files: <strong>{features.config_files_changed}</strong></span>
      </div>
    </div>
  );
}
