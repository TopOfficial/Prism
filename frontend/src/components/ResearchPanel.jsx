import { useState, useEffect, useRef } from "react";
import { supabase } from "../lib/supabase";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Markdown element styles matching Prism dark theme
const MD = {
  h1: ({ children }) => (
    <h1 style={{ fontFamily: "'Cinzel', serif", color: "#A855F7", fontSize: 20, letterSpacing: "0.1em", marginBottom: 12, marginTop: 24 }}>{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 style={{ color: "#A855F7", fontSize: 16, fontWeight: 700, marginBottom: 10, marginTop: 20, fontFamily: "'Space Grotesk', sans-serif" }}>{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 style={{ color: "#CBD5E1", fontSize: 14, fontWeight: 600, marginBottom: 8, marginTop: 16, fontFamily: "'Space Grotesk', sans-serif", textTransform: "uppercase", letterSpacing: "0.08em" }}>{children}</h3>
  ),
  p: ({ children }) => (
    <p style={{ color: "#94A3B8", fontSize: 14, lineHeight: 1.7, marginBottom: 10 }}>{children}</p>
  ),
  strong: ({ children }) => (
    <strong style={{ color: "#E2E8F0", fontWeight: 600 }}>{children}</strong>
  ),
  hr: () => (
    <hr style={{ border: "none", borderTop: "1px solid rgba(168,85,247,0.15)", margin: "20px 0" }} />
  ),
  ul: ({ children }) => (
    <ul style={{ paddingLeft: 20, marginBottom: 10 }}>{children}</ul>
  ),
  ol: ({ children }) => (
    <ol style={{ paddingLeft: 20, marginBottom: 10 }}>{children}</ol>
  ),
  li: ({ children }) => (
    <li style={{ color: "#94A3B8", fontSize: 14, lineHeight: 1.7, marginBottom: 4 }}>{children}</li>
  ),
  table: ({ children }) => (
    <div style={{ overflowX: "auto", marginBottom: 16 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, fontFamily: "'Fira Code', monospace" }}>{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead style={{ borderBottom: "1px solid rgba(168,85,247,0.3)" }}>{children}</thead>
  ),
  th: ({ children }) => (
    <th style={{ textAlign: "left", padding: "8px 12px", color: "#A855F7", fontSize: 12, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif", textTransform: "uppercase", letterSpacing: "0.05em" }}>{children}</th>
  ),
  td: ({ children }) => (
    <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{children}</td>
  ),
  blockquote: ({ children }) => (
    <blockquote style={{ borderLeft: "3px solid rgba(168,85,247,0.4)", paddingLeft: 14, marginLeft: 0, marginBottom: 10 }}>{children}</blockquote>
  ),
  code: ({ inline, children }) => inline
    ? <code style={{ background: "rgba(168,85,247,0.12)", color: "#C4B5FD", padding: "1px 5px", borderRadius: 4, fontSize: 13, fontFamily: "'Fira Code', monospace" }}>{children}</code>
    : <pre style={{ background: "rgba(0,0,0,0.3)", padding: 14, borderRadius: 8, overflow: "auto", fontSize: 13, fontFamily: "'Fira Code', monospace", color: "#94A3B8", marginBottom: 10 }}><code>{children}</code></pre>,
};

function PhaseIndicator({ active }) {
  const phases = ["Core Metrics", "Bull vs Bear", "Stress Test"];
  return (
    <div className="flex items-center gap-3 mt-3">
      {phases.map((p, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: active > i ? "#A855F7" : "rgba(168,85,247,0.25)",
            boxShadow: active > i ? "0 0 8px #A855F7" : "none",
            transition: "all 0.5s",
          }} />
          <span style={{ fontSize: 11, color: active > i ? "#A855F7" : "#2D3D50", fontFamily: "'Space Grotesk', sans-serif" }}>{p}</span>
          {i < 2 && <span style={{ color: "#2D3D50", fontSize: 11 }}>→</span>}
        </div>
      ))}
    </div>
  );
}

export default function ResearchPanel({ ticker, user, isPro, apiBase, onUpgrade }) {
  const [status, setStatus] = useState("idle"); // idle | locked | loading | done | error
  const [report, setReport] = useState(null);
  const [errMsg, setErrMsg] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    setStatus("idle");
    setReport(null);
    setErrMsg(null);
    setElapsed(0);
  }, [ticker]);

  useEffect(() => {
    if (status === "loading") {
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    } else {
      clearInterval(timerRef.current);
      if (status !== "loading") setElapsed(0);
    }
    return () => clearInterval(timerRef.current);
  }, [status]);

  async function handleRun() {
    if (!isPro) { setStatus("locked"); return; }

    setStatus("loading");
    setReport(null);
    setErrMsg(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${apiBase}/research/${ticker}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        if (body.detail === "pro_required") { setStatus("locked"); return; }
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setReport(data.report);
      setStatus("done");
    } catch (e) {
      setErrMsg(e.message || "Analysis failed");
      setStatus("error");
    }
  }

  const phaseGuess = elapsed < 15 ? 0 : elapsed < 30 ? 1 : 2;

  return (
    <div
      className="animate-fade-in-up rounded-2xl overflow-hidden"
      style={{ background: "rgba(168,85,247,0.04)", border: "1px solid rgba(168,85,247,0.18)", marginTop: 4 }}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between px-5 py-4"
        style={{ borderBottom: status === "done" ? "1px solid rgba(168,85,247,0.15)" : "none" }}>
        <div className="flex items-center gap-3">
          <div style={{ width: 3, height: 14, borderRadius: 9, background: "#A855F7", boxShadow: "0 0 8px #A855F7" }} />
          <h3 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
            Deep Research
          </h3>
          <span className="text-xs px-2 py-0.5 rounded-full font-semibold"
            style={{ background: "rgba(168,85,247,0.15)", color: "#A855F7", border: "1px solid rgba(168,85,247,0.3)", fontFamily: "'Space Grotesk', sans-serif" }}>
            Pro
          </span>
        </div>

        {status === "done" && (
          <button onClick={() => { setStatus("idle"); setReport(null); }}
            style={{ fontSize: 12, color: "#3D5068", background: "none", border: "none", cursor: "pointer" }}>
            Clear
          </button>
        )}
      </div>

      {/* Body */}
      <div className="px-5 py-4">

        {/* IDLE — show run button for everyone */}
        {status === "idle" && (
          <div className="flex items-center justify-between">
            <p className="text-sm" style={{ color: "#64748B" }}>
              3-phase institutional analysis of <span style={{ color: "#A855F7" }}>{ticker}</span>. Takes ~1-2 minutes.
            </p>
            <button onClick={handleRun}
              className="text-sm font-semibold px-4 py-2 rounded-xl cursor-pointer transition-all ml-4 shrink-0"
              style={{ background: "rgba(168,85,247,0.18)", border: "1px solid rgba(168,85,247,0.4)", color: "#A855F7" }}
              onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.28)"}
              onMouseLeave={e => e.currentTarget.style.background = "rgba(168,85,247,0.18)"}>
              Run Deep Analysis
            </button>
          </div>
        )}

        {/* LOCKED — non-pro clicked the button */}
        {status === "locked" && (
          <div className="text-center py-6 animate-fade-in">
            <div style={{ fontSize: 28, marginBottom: 10 }}>🔒</div>
            <p className="text-sm font-semibold mb-1" style={{ color: "#E2E8F0" }}>Pro feature</p>
            <p className="text-sm mb-5" style={{ color: "#64748B" }}>
              {!user
                ? "Sign in and upgrade to Pro to run 3-phase institutional analysis."
                : "Upgrade to Pro to unlock unlimited Deep Research reports."}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button onClick={() => onUpgrade(user ? "monthly" : undefined)}
                className="text-sm font-semibold px-5 py-2.5 rounded-xl cursor-pointer"
                style={{ background: "#A855F7", border: "none", color: "#fff" }}>
                {user ? "Upgrade to Pro — ฿199/mo" : "Sign In to Unlock"}
              </button>
              <button onClick={() => setStatus("idle")}
                style={{ fontSize: 12, color: "#3D5068", background: "none", border: "none", cursor: "pointer" }}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* LOADING */}
        {status === "loading" && (
          <div className="py-6 text-center">
            <div style={{
              width: 32, height: 32, border: "2px solid rgba(168,85,247,0.2)",
              borderTop: "2px solid #A855F7", borderRadius: "50%",
              animation: "spin 0.8s linear infinite", margin: "0 auto 12px",
            }} />
            <p className="text-sm font-medium" style={{ color: "#A855F7" }}>
              Claude is analyzing {ticker}… ({elapsed}s)
            </p>
            <PhaseIndicator active={phaseGuess} />
          </div>
        )}

        {/* ERROR */}
        {status === "error" && (
          <div className="py-4">
            <p className="text-sm mb-3" style={{ color: "#F87171" }}>{errMsg}</p>
            <button onClick={() => setStatus("idle")} style={{ fontSize: 12, color: "#4E6278", background: "none", border: "none", cursor: "pointer" }}>
              ← Try again
            </button>
          </div>
        )}

        {/* DONE — report */}
        {status === "done" && report && (
          <div style={{ maxWidth: "100%" }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD}>
              {report}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
