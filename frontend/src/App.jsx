import { useState, useEffect } from "react";
import { supabase } from "./lib/supabase";
import SearchBar from "./components/SearchBar";
import BriefCard from "./components/BriefCard";
import LeftPanel from "./components/LeftPanel";
import LoadingState from "./components/LoadingState";
import ErrorState from "./components/ErrorState";
import HelpModal from "./components/HelpModal";
import AuthModal from "./components/AuthModal";
import ResearchPanel from "./components/ResearchPanel";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [ticker, setTicker] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showHelp, setShowHelp] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) setShowAuth(false);
    });
    return () => subscription.unsubscribe();
  }, []);

  async function _authHeaders() {
    const { data: { session } } = await supabase.auth.getSession();
    return session ? { Authorization: `Bearer ${session.access_token}` } : {};
  }

  async function handleSearch(t) {
    setTicker(t);
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const headers = await _authHeaders();
      const res = await fetch(`${API}/brief/${t}`, { headers });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        if (body.detail === "daily_limit_reached") {
          setError("daily_limit_reached");
          return;
        }
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
  }

  async function handleUpgrade(plan = "monthly") {
    if (!user) { setShowAuth(true); return; }
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${API}/create-checkout-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ plan }),
      });
      const body = await res.json();
      if (body.checkout_url) window.location.href = body.checkout_url;
    } catch (e) {
      console.error("Upgrade error:", e);
    }
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden" style={{ background: "#070B14" }}>

      {/* ── Animated background ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        <div style={{
          position: "absolute", width: 700, height: 700,
          top: "-25%", left: "-15%",
          background: "radial-gradient(circle, rgba(168,85,247,0.09) 0%, transparent 65%)",
          animation: "orbFloat1 22s ease-in-out infinite",
          borderRadius: "50%",
        }} />
        <div style={{
          position: "absolute", width: 600, height: 600,
          bottom: "-20%", right: "-15%",
          background: "radial-gradient(circle, rgba(252,211,77,0.07) 0%, transparent 65%)",
          animation: "orbFloat2 28s ease-in-out infinite",
          borderRadius: "50%",
        }} />
        <div style={{
          position: "absolute", width: 400, height: 400,
          top: "40%", left: "55%",
          background: "radial-gradient(circle, rgba(168,85,247,0.05) 0%, transparent 70%)",
          animation: "orbFloat3 18s ease-in-out infinite",
          borderRadius: "50%",
        }} />
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

          <div className="flex items-center gap-2 mt-1">
            {user ? (
              <>
                {!data?.is_pro && (
                  <button onClick={() => handleUpgrade("monthly")}
                    className="text-xs font-semibold px-3 py-2 rounded-lg cursor-pointer transition-all duration-200"
                    style={{ background: "rgba(168,85,247,0.18)", border: "1px solid rgba(168,85,247,0.4)", color: "#A855F7" }}
                    onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.28)"}
                    onMouseLeave={e => e.currentTarget.style.background = "rgba(168,85,247,0.18)"}>
                    Upgrade to Pro
                  </button>
                )}
                <button onClick={handleSignOut}
                  className="text-xs px-3 py-2 rounded-lg cursor-pointer transition-all duration-200"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#4E6278" }}
                  onMouseEnter={e => e.currentTarget.style.color = "#64748B"}
                  onMouseLeave={e => e.currentTarget.style.color = "#4E6278"}>
                  {user.email?.split("@")[0]}  ·  Sign Out
                </button>
              </>
            ) : (
              <button onClick={() => setShowAuth(true)}
                className="text-xs font-medium px-3 py-2 rounded-lg cursor-pointer transition-all duration-200"
                style={{ background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.22)", color: "#A855F7" }}
                onMouseEnter={e => { e.currentTarget.style.background = "rgba(168,85,247,0.14)"; }}
                onMouseLeave={e => { e.currentTarget.style.background = "rgba(168,85,247,0.07)"; }}>
                Sign In
              </button>
            )}

            <button onClick={() => setShowHelp(true)} aria-label="Help"
              className="flex items-center gap-2 text-xs font-medium rounded-lg px-3 py-2 cursor-pointer transition-all duration-200"
              style={{ background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.22)", color: "#A855F7" }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(168,85,247,0.14)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(168,85,247,0.07)"; }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>
              </svg>
              Help
            </button>
          </div>
        </header>

        {/* Search */}
        <div className="animate-fade-in-up" style={{ animationDelay: "0.08s" }}>
          <SearchBar onSubmit={handleSearch} loading={loading} />
        </div>

        {/* Daily limit gate */}
        {error === "daily_limit_reached" && (
          <div className="mt-6 rounded-2xl p-6 text-center animate-fade-in"
            style={{ background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.25)" }}>
            <p className="text-sm font-semibold mb-1" style={{ color: "#A855F7" }}>Daily limit reached</p>
            <p className="text-sm mb-4" style={{ color: "#64748B" }}>Free accounts get 5 searches/day.</p>
            <button onClick={() => handleUpgrade("monthly")}
              className="text-sm font-semibold px-5 py-2.5 rounded-xl cursor-pointer transition-all"
              style={{ background: "#A855F7", border: "none", color: "#fff" }}>
              Upgrade to Pro — ฿199/mo
            </button>
          </div>
        )}

        {/* Results */}
        <main className="mt-6">
          {loading && <LoadingState ticker={ticker} />}
          {error && error !== "daily_limit_reached" && <ErrorState ticker={ticker} message={error} />}
          {data && (
            <div className="flex flex-col gap-4 pb-12">
              <div className="flex flex-col lg:flex-row lg:items-start gap-4">
                <div className="flex-1 min-w-0">
                  <BriefCard data={data} />
                </div>
                <div className="lg:w-[400px] xl:w-[440px] shrink-0 lg:sticky lg:top-6">
                  <LeftPanel data={data} apiBase={API} user={user} onUpgrade={handleUpgrade} />
                </div>
              </div>
              <ResearchPanel
                ticker={data.ticker}
                user={user}
                isPro={!!data.is_pro}
                apiBase={API}
                onUpgrade={handleUpgrade}
              />
            </div>
          )}
        </main>
      </div>

      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}
