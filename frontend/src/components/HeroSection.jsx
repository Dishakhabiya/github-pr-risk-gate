import React, { useEffect, useRef, useState } from "react";

const TAGLINES = ["risk awareness", "code quality", "safe merging", "team alignment"];

export default function HeroSection({ onStart }) {
  const [taglineIndex, setTaglineIndex] = useState(0);
  const [scrollProgress, setScrollProgress] = useState(0);
  const wrapperRef = useRef(null);

  // Cycle tagline
  useEffect(() => {
    const id = setInterval(
      () => setTaglineIndex((i) => (i + 1) % TAGLINES.length),
      2500
    );
    return () => clearInterval(id);
  }, []);

  // Scroll-driven card reveal
  useEffect(() => {
    const onScroll = () => {
      const el = wrapperRef.current;
      if (!el) return;
      const { top, height } = el.getBoundingClientRect();
      // total scrollable distance inside the sticky container
      const scrollable = height - window.innerHeight;
      const scrolled = -top;
      // progress: 0 → card hidden inside, 1 → card fully emerged
      const p = Math.min(1, Math.max(0, scrolled / (scrollable * 0.65)));
      setScrollProgress(p);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Card y: 100% = fully inside envelope, -55% = fully emerged above
  const cardY = 100 - scrollProgress * 155;

  return (
    <section className="hero-wrapper" ref={wrapperRef}>
      <div className="hero-sticky">

        {/* Tagline floats top-centre */}
        <p className="hero-tagline">
          Building through{" "}
          <em className="hero-tagline-word" key={taglineIndex}>
            {TAGLINES[taglineIndex]}
          </em>
        </p>

        {/* Scene: envelope + emerging paper */}
        <div className="hero-scene">

          {/* ── PAPER CARD (z-index 2 — between envelope back and front) ── */}
          <div
            className="hero-paper"
            style={{ transform: `translateX(-50%) translateY(${cardY}%)` }}
          >
            <div className="hero-paper-inner">
              <span className="hero-paper-star">✳</span>

              <h1 className="hero-paper-title">
                GitHub PR<br />Risk Gate
              </h1>

              <p className="hero-paper-desc">
                AI-powered risk assessment &amp; merge gating —
                analysing every pull request so your team ships with confidence.
              </p>

              {/* Track rows, like Bharat Digital fellowship steps */}
              <div className="hero-paper-tracks">
                <div className="hero-track-row">
                  <div>
                    <span className="hero-track-num">STEP 1</span>
                    <span className="hero-track-name">PR Analysis</span>
                  </div>
                  <button className="hero-track-btn" onClick={onStart}>
                    Analyse now
                  </button>
                </div>
                <div className="hero-track-row">
                  <div>
                    <span className="hero-track-num">STEP 2</span>
                    <span className="hero-track-name">Risk Prediction</span>
                  </div>
                </div>
                <div className="hero-track-row">
                  <div>
                    <span className="hero-track-num">STEP 3</span>
                    <span className="hero-track-name">PR Understanding</span>
                  </div>
                </div>
                <div className="hero-track-row hero-track-row--last">
                  <div>
                    <span className="hero-track-num">STEP 4</span>
                    <span className="hero-track-name">Merge Decision</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ── ENVELOPE BACK (z-index 1, behind card) ── */}
          <div className="hero-env-back">
            <div className="hero-env-back-flap" />
          </div>

          {/* ── ENVELOPE FRONT BODY (z-index 3, covers card bottom — creates "inside" illusion) ── */}
          <div className="hero-env-front">
            <div className="hero-env-front-flap" />
            <span className="hero-env-label">GITHUB PR RISK GATE</span>
          </div>
        </div>

        {/* Scroll nudge */}
        <p
          className="hero-scroll-hint"
          style={{ opacity: scrollProgress < 0.08 ? 1 : 0 }}
        >
          scroll to open ↓
        </p>
      </div>
    </section>
  );
}
