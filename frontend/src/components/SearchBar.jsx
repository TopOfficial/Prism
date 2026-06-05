import { useState } from "react";

export default function SearchBar({ onSubmit, loading }) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    const t = value.trim().toUpperCase();
    if (t) onSubmit(t);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full" role="search">
      <div
        className="flex gap-2 p-1.5 rounded-xl transition-all duration-300"
        style={{
          background: "rgba(10, 15, 30, 0.92)",
          border: `1px solid ${focused ? "rgba(168,85,247,0.55)" : "rgba(168,85,247,0.18)"}`,
          boxShadow: focused
            ? "0 0 0 3px rgba(168,85,247,0.1), 0 0 24px rgba(168,85,247,0.18)"
            : "none",
        }}
      >
        {/* Search icon */}
        <div className="flex items-center pl-2.5 shrink-0" style={{ color: focused ? "#A855F7" : "#475569", transition: "color 0.2s" }}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
        </div>

        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Ticker symbol — AAPL, TSLA, NVDA..."
          className="flex-1 bg-transparent text-white focus:outline-none text-sm py-2 min-w-0"
          style={{
            fontFamily: "'Fira Code', monospace",
            color: "#E2E8F0",
          }}
          disabled={loading}
          autoFocus
          autoComplete="off"
          spellCheck="false"
          aria-label="Stock ticker symbol"
        />

        <button
          type="submit"
          disabled={loading || !value.trim()}
          className="shrink-0 px-5 py-2 rounded-lg text-sm font-semibold cursor-pointer transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: loading
              ? "rgba(168,85,247,0.15)"
              : "linear-gradient(135deg, #A855F7 0%, #7C3AED 100%)",
            color: loading ? "#A855F7" : "#F5F0FF",
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 600,
            boxShadow: loading ? "none" : "0 0 18px rgba(168,85,247,0.45)",
          }}
          onMouseEnter={e => { if (!loading && value.trim()) e.currentTarget.style.boxShadow = "0 0 28px rgba(168,85,247,0.65)"; }}
          onMouseLeave={e => { if (!loading) e.currentTarget.style.boxShadow = value.trim() ? "0 0 18px rgba(168,85,247,0.45)" : "none"; }}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg
                width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                style={{ animation: "spinnerArc 0.8s linear infinite" }}
              >
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
              Analyzing
            </span>
          ) : "Analyze"}
        </button>
      </div>
    </form>
  );
}
