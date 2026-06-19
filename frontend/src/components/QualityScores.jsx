import { useEffect, useState } from "react";

function ScoreBar({ label, score, color, delay }) {
  const [fill, setFill] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setFill(true), delay + 200);
    return () => clearTimeout(t);
  }, [delay]);

  const pct = `${(score / 10) * 100}%`;
  const textColor = score >= 7 ? "#34D399" : score >= 5 ? "#FCD34D" : "#F87171";

  return (
    <div>
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-xs" style={{ color: "#64748B", fontFamily: "'Inter', sans-serif" }}>{label}</span>
        <span
          className="font-mono text-sm font-semibold"
          style={{
            color: textColor,
            fontFamily: "'Fira Code', monospace",
            textShadow: `0 0 8px ${textColor}70`,
          }}
        >
          {score}/10
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.05)" }}>
        <div
          style={{
            height: "100%",
            borderRadius: "9999px",
            width: fill ? pct : "0%",
            background: `linear-gradient(90deg, ${color}50, ${color})`,
            boxShadow: `0 0 8px ${color}70`,
            transition: "width 0.9s cubic-bezier(0.34, 1.56, 0.64, 1)",
          }}
        />
      </div>
    </div>
  );
}

export default function QualityScores({ scores }) {
  // Hooks must run unconditionally and in the same order every render, so they go
  // before any early return (Rules of Hooks).
  const [drawn, setDrawn] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDrawn(true), 100);
    return () => clearTimeout(t);
  }, []);

  if (!scores) return null;

  const overall = scores.overall;
  const overallColor = overall >= 7 ? "#34D399" : overall >= 5 ? "#FCD34D" : "#F87171";
  const circumference = 2 * Math.PI * 26;

  const dims = [
    { label: "Business Quality",    key: "business_quality",        color: "#A855F7" },
    { label: "Financial Health",     key: "financial_health",         color: "#34D399" },
    { label: "Valuation",            key: "valuation_attractiveness", color: "#FCD34D" },
    { label: "Growth Outlook",       key: "growth_outlook",           color: "#A78BFA" },
  ];

  return (
    <div>
      {/* Overall circle + bars row */}
      <div className="flex gap-5 items-start mb-4">
        {/* SVG circle */}
        <div className="relative flex items-center justify-center shrink-0" style={{ width: 72, height: 72 }}>
          <svg width="72" height="72" viewBox="0 0 60 60">
            <circle cx="30" cy="30" r="26" fill="none" stroke={`${overallColor}18`} strokeWidth="4" />
            <circle
              cx="30" cy="30" r="26"
              fill="none"
              stroke={overallColor}
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={drawn ? circumference * (1 - overall / 10) : circumference}
              transform="rotate(-90 30 30)"
              style={{
                transition: "stroke-dashoffset 1.1s cubic-bezier(0.34, 1.56, 0.64, 1)",
                filter: `drop-shadow(0 0 6px ${overallColor}90)`,
              }}
            />
          </svg>
          <span
            className="absolute font-mono font-bold text-lg"
            style={{ color: overallColor, fontFamily: "'Fira Code', monospace", textShadow: `0 0 10px ${overallColor}80` }}
          >
            {overall}
          </span>
        </div>

        <div className="flex-1 space-y-3 pt-1">
          {dims.map((d, i) => (
            <ScoreBar key={d.key} label={d.label} score={scores[d.key]} color={d.color} delay={i * 80} />
          ))}
        </div>
      </div>

      {/* Signals */}
      {scores.signals?.length > 0 && (
        <div className="space-y-1.5 mt-2">
          {scores.signals.map((s, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-xs px-3 py-2.5 rounded-lg"
              style={{
                background: "rgba(168,85,247,0.05)",
                border: "1px solid rgba(168,85,247,0.12)",
                animation: `fadeInUp 0.4s cubic-bezier(0.16,1,0.3,1) ${0.3 + i * 0.07}s both`,
              }}
            >
              <span style={{ color: "#A855F7", marginTop: 1, flexShrink: 0 }}>›</span>
              <span style={{ color: "#94A3B8", lineHeight: 1.5 }}>{s}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
