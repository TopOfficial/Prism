import { useState } from "react";
import SearchBar from "./components/SearchBar";
import BriefCard from "./components/BriefCard";
import LeftPanel from "./components/LeftPanel";
import LoadingState from "./components/LoadingState";
import ErrorState from "./components/ErrorState";
import HelpModal from "./components/HelpModal";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [ticker, setTicker] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showHelp, setShowHelp] = useState(false);

  async function handleSearch(t) {
    setTicker(t);
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await fetch(`${API}/brief/${t}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden" style={{ background: "#070B14" }}>

      {/* ── Animated background ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        {/* Purple orb top-left */}
        <div style={{
          position: "absolute", width: 700, height: 700,
          top: "-25%", left: "-15%",
          background: "radial-gradient(circle, rgba(168,85,247,0.09) 0%, transparent 65%)",
          animation: "orbFloat1 22s ease-in-out infinite",
          borderRadius: "50%",
        }} />
        {/* Yellow orb bottom-right */}
        <div style={{
          position: "absolute", width: 600, height: 600,
          bottom: "-20%", right: "-15%",
          background: "radial-gradient(circle, rgba(252,211,77,0.07) 0%, transparent 65%)",
          animation: "orbFloat2 28s ease-in-out infinite",
          borderRadius: "50%",
        }} />
        {/* Purple mid orb */}
        <div style={{
          position: "absolute", width: 400, height: 400,
          top: "40%", left: "55%",
          background: "radial-gradient(circle, rgba(168,85,247,0.05) 0%, transparent 70%)",
          animation: "orbFloat3 18s ease-in-out infinite",
          borderRadius: "50%",
        }} />
        {/* Subtle grid */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: "linear-gradient(rgba(168,85,247,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(168,85,247,0.025) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
        }} />
      </div>

      {/* ── Main content ── */}
      <div className="relative z-10 w-full max-w-[1500px] mx-auto px-4 sm:px-6 xl:px-10 py-8 sm:py-10">

        {/* Header */}
        <header className="flex items-start justify-between mb-10 animate-fade-in">
          <div>
            <h1 className="text-3xl sm:text-4xl"
              style={{ fontFamily: "'Cinzel', serif", fontWeight: 500, letterSpacing: "0.18em", color: "#A855F7", textShadow: "0 0 28px rgba(168,85,247,0.6)", textTransform: "uppercase" }}>
              Prism
            </h1>
            <p className="text-sm mt-1" style={{ color: "#475569" }}>Investment intelligence, instantly.</p>
          </div>
          <button
            onClick={() => setShowHelp(true)}
            aria-label="Help — what each section means"
            className="flex items-center gap-2 text-xs font-medium rounded-lg px-3 py-2 cursor-pointer transition-all duration-200 mt-1"
            style={{
              background: "rgba(168,85,247,0.07)",
              border: "1px solid rgba(168,85,247,0.22)",
              color: "#A855F7",
              fontFamily: "'Space Grotesk', sans-serif",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = "rgba(168,85,247,0.14)";
              e.currentTarget.style.boxShadow = "0 0 16px rgba(168,85,247,0.22)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = "rgba(168,85,247,0.07)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>
            </svg>
            Help
          </button>
        </header>

        {/* Search */}
        <div className="animate-fade-in-up" style={{ animationDelay: "0.08s" }}>
          <SearchBar onSubmit={handleSearch} loading={loading} />
        </div>

        {/* Results */}
        <main className="mt-6">
          {loading && <LoadingState ticker={ticker} />}
          {error && <ErrorState ticker={ticker} message={error} />}
          {data && (
            <div className="flex flex-col lg:flex-row lg:items-start gap-4 pb-12">
              {/* Left — company data */}
              <div className="flex-1 min-w-0">
                <BriefCard data={data} />
              </div>
              {/* Right — verdict + scores + valuation + news (sticky on desktop) */}
              <div className="lg:w-[400px] xl:w-[440px] shrink-0 lg:sticky lg:top-6">
                <LeftPanel data={data} apiBase={API} />
              </div>
            </div>
          )}
        </main>
      </div>

      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}
    </div>
  );
}
