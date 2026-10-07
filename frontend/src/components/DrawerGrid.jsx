import React, { useState } from "react";

const DRAWERS = [
  {
    id: "analysis",
    label: "PR ANALYSIS",
    desc: "Fetch and ingest PR metadata, diff stats, and file-level changes from GitHub.",
    step: "01",
  },
  {
    id: "risk",
    label: "RISK PREDICTION",
    desc: "ML model evaluates creation-time features and returns a risk score & level.",
    step: "02",
  },
  {
    id: "understanding",
    label: "PR UNDERSTANDING",
    desc: "RAG-retrieved code context plus LLM-generated comprehension questions for the author.",
    step: "03",
  },
  {
    id: "result",
    label: "MERGE DECISION",
    desc: "Final LLM evaluation synthesises ML score and developer understanding into PASS / BLOCK.",
    step: "04",
  },
];

export default function DrawerGrid({ onSelectStep }) {
  const [hovered, setHovered] = useState(null);

  return (
    <section className="drawer-section">
      <h2 className="drawer-section-title">
        The four-step pipeline for<br />every pull request
      </h2>

      {/* Single-column vertical filing cabinet */}
      <div className="cabinet-outer">
        <div className="cabinet-grid">
          {DRAWERS.map((d) => (
            <div key={d.id} className="drawer-slot">
              {/*
                The drawer-card is position:absolute inset:0 inside the slot.
                On hover it translateY(-75px) upward — revealing dark slot interior.
                The left-side 3D panel is a ::before pseudo-element that becomes
                visible when the card has class drawer-card--open.
              */}
              <div
                className={`drawer-card${hovered === d.id ? " drawer-card--open" : ""}`}
                onMouseEnter={() => setHovered(d.id)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => onSelectStep(d.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && onSelectStep(d.id)}
              >
                {/* Tooltip rides with the sliding card — floats above cabinet on open */}
                {hovered === d.id && (
                  <div className="drawer-tooltip">{d.desc}</div>
                )}

                {/* Inner panel matching the image 01 sketch style */}
                <div className="drawer-inner-rect">
                  {/* Label tag — the paper holder at the top left of each drawer */}
                  <div className="drawer-label-strip">
                    <span className="drawer-label">{d.label}</span>
                    <span className="drawer-step-num">{d.step}</span>
                  </div>

                  {/* Pull knob centered in the drawer body */}
                  <div className="drawer-body">
                    <div className="drawer-knob" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
