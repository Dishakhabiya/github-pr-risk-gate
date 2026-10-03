import React from "react";
import { BookOpen, FileCode, Database } from "lucide-react";

export default function RepositoryContext({ contextList }) {
  if (!contextList || contextList.length === 0) {
    return (
      <div className="card-container">
        <div className="card-header">
          <BookOpen size={20} />
          <h3 className="card-title">Repository Context (RAG)</h3>
        </div>
        <p className="text-muted">No repository context retrieved yet.</p>
      </div>
    );
  }

  return (
    <div className="card-container">
      <div className="card-header">
        <div className="card-header-icon text-teal">
          <Database size={20} />
        </div>
        <div>
          <h2 className="card-title">Retrieved Repository Context (RAG)</h2>
          <p className="card-description">
            Person 2 Vector Database context snippets relevant to the PR's code changes.
          </p>
        </div>
      </div>

      <div className="snippets-list">
        {contextList.map((item, idx) => (
          <div key={idx} className="snippet-card">
            <div className="snippet-header">
              <FileCode size={16} />
              <span className="snippet-file">{item.file}</span>
              <span className="snippet-lines">{item.lines}</span>
            </div>
            <pre className="code-block">
              <code>{item.snippet}</code>
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
