import { useState, useRef, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

export default function SearchBar({ onSubmit, loading, initialValue = "" }) {
  const [value, setValue] = useState(initialValue);
  const [focused, setFocused] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [highlighted, setHighlighted] = useState(-1);
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);

  const fetchSuggestions = useCallback(debounce(async (q) => {
    if (q.length < 1) { setSuggestions([]); return; }
    try {
      const res = await fetch(`${API}/search?q=${encodeURIComponent(q)}`);
      if (res.ok) setSuggestions(await res.json());
    } catch { setSuggestions([]); }
  }, 200), []);

  useEffect(() => {
    fetchSuggestions(value);
    setHighlighted(-1);
  }, [value]);

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e) {
      if (!dropdownRef.current?.contains(e.target) && !inputRef.current?.contains(e.target)) {
        setSuggestions([]);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function selectSuggestion(symbol) {
    setValue(symbol);
    setSuggestions([]);
    onSubmit(symbol);
  }

  function handleSubmit(e) {
    e.preventDefault();
    const t = value.trim().toUpperCase();
    if (t) { setSuggestions([]); onSubmit(t); }
  }

  function handleKeyDown(e) {
    if (!suggestions.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setHighlighted(h => Math.min(h + 1, suggestions.length - 1)); }
    if (e.key === "ArrowUp")   { e.preventDefault(); setHighlighted(h => Math.max(h - 1, -1)); }
    if (e.key === "Enter" && highlighted >= 0) { e.preventDefault(); selectSuggestion(suggestions[highlighted].symbol); }
    if (e.key === "Escape") setSuggestions([]);
  }

  const showDropdown = focused && suggestions.length > 0 && !loading;

  return (
    <div className="w-full relative">
      <form onSubmit={handleSubmit} role="search">
        <div
          className="flex gap-2 p-1.5 rounded-xl transition-all duration-300"
          style={{
            background: "rgba(10, 15, 30, 0.92)",
            border: `1px solid ${focused ? "rgba(168,85,247,0.55)" : "rgba(168,85,247,0.18)"}`,
            boxShadow: focused ? "0 0 0 3px rgba(168,85,247,0.1), 0 0 24px rgba(168,85,247,0.18)" : "none",
          }}
        >
          <div className="flex items-center pl-2.5 shrink-0" style={{ color: focused ? "#A855F7" : "#475569", transition: "color 0.2s" }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </div>

          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value.toUpperCase())}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder="Ticker symbol — AAPL, TSLA, NVDA..."
            className="flex-1 bg-transparent text-white focus:outline-none text-sm py-2 min-w-0"
            style={{ fontFamily: "'Fira Code', monospace", color: "#E2E8F0" }}
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
              background: loading ? "rgba(168,85,247,0.15)" : "linear-gradient(135deg, #A855F7 0%, #7C3AED 100%)",
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
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" style={{ animation: "spinnerArc 0.8s linear infinite" }}>
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
                Analyzing
              </span>
            ) : "Analyze"}
          </button>
        </div>
      </form>

      {/* Autocomplete dropdown */}
      {showDropdown && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 rounded-xl overflow-hidden animate-fade-in"
          style={{ background: "rgba(10,15,30,0.97)", border: "1px solid rgba(168,85,247,0.25)", boxShadow: "0 8px 32px rgba(0,0,0,0.5)" }}
        >
          {suggestions.map((s, i) => (
            <div
              key={s.symbol}
              onMouseDown={() => selectSuggestion(s.symbol)}
              className="flex items-center justify-between px-4 py-2.5 cursor-pointer transition-colors"
              style={{ background: highlighted === i ? "rgba(168,85,247,0.12)" : "transparent" }}
              onMouseEnter={() => setHighlighted(i)}
              onMouseLeave={() => setHighlighted(-1)}
            >
              <span style={{ fontFamily: "'Fira Code', monospace", color: "#A855F7", fontSize: 13, fontWeight: 600 }}>{s.symbol}</span>
              <span style={{ color: "#475569", fontSize: 12, marginLeft: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "60%" }}>{s.name}</span>
              <span style={{ color: "#2D3D50", fontSize: 11, marginLeft: 8, flexShrink: 0 }}>{s.exchange}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
