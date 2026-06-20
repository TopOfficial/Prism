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
import PricingModal from "./components/PricingModal";
import HistorySidebar from "./components/HistorySidebar";
import { Analytics } from "@vercel/analytics/react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const EMPTY_ACCOUNT = { is_admin: false, is_subscriber: false, credits: 0, free_research_available: false, next_free_research_at: null };

function loadCachedAccount() {
  try {
    const raw = localStorage.getItem("prism_account");
    return raw ? { ...EMPTY_ACCOUNT, ...JSON.parse(raw) } : EMPTY_ACCOUNT;
  } catch {
    return EMPTY_ACCOUNT;
  }
}

function EmptyTab({ text }) {
  return (
    <div className="glass-card p-10 text-center animate-fade-in-up" style={{ color: "#3D5068", fontSize: 14 }}>
      {text}
    </div>
  );
}

export default function App() {
  const [ticker, setTicker] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showHelp, setShowHelp] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [showPricing, setShowPricing] = useState(false);
  const [user, setUser] = useState(null);
  const [account, setAccount] = useState(loadCachedAccount);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState("brief");

  // A user can run a fresh analysis if they're admin, subscribed, have a free weekly run, or hold credits.
  const canRunResearch =
    account.is_admin || account.is_subscriber || account.free_research_available || account.credits > 0;

  function setAccountCached(acct) {
    const next = { ...EMPTY_ACCOUNT, ...acct };
    setAccount(next);
    localStorage.setItem("prism_account", JSON.stringify(next));
  }

  async function fetchAccount(session) {
    if (!session) { setAccountCached(EMPTY_ACCOUNT); return; }
    try {
      const res = await fetch(`${API}/me`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) setAccountCached(await res.json());
    } catch {
      // keep cached value on network error
    }
  }

  async function fetchHistory(session) {
    if (!session) { setHistory([]); return; }
    try {
      const res = await fetch(`${API}/history`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.ok) {
        const body = await res.json();
        setHistory(body.items || []);
      }
    } catch {
      setHistory([]);
    }
  }

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      fetchAccount(session);
      fetchHistory(session);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) setShowAuth(false);
      fetchAccount(session);
      fetchHistory(session);
    });
    return () => subscription.unsubscribe();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- run once on mount

  // Returning from a successful Stripe checkout: refresh entitlements and clean the URL.
  // The webhook that grants credits may land a beat after the redirect, so refetch twice.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("purchased") !== "1") return;
    const refresh = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      fetchAccount(session);
      fetchHistory(session);
    };
    refresh();
    const t = setTimeout(refresh, 3000);
    setShowPricing(false);
    window.history.replaceState({}, "", window.location.pathname);
    return () => clearTimeout(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- run once on mount

  async function _authHeaders() {
    const { data: { session } } = await supabase.auth.getSession();
    return session ? { Authorization: `Bearer ${session.access_token}` } : {};
  }

  async function handleSearch(t, { tab = "brief" } = {}) {
    setTicker(t);
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const headers = await _authHeaders();
      const res = await fetch(`${API}/brief/${t}`, { headers });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const json = await res.json();
      setData(json);
      setActiveTab(tab);
    } catch (e) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  // Open a ticker from the History tab → load its brief and land on the Deep Research report.
  function openFromHistory(t) {
    handleSearch(t, { tab: "research" });
  }

  // Called by ResearchPanel after a fresh run so credits + history stay in sync.
  async function refreshAfterRun() {
    const { data: { session } } = await supabase.auth.getSession();
    fetchAccount(session);
    fetchHistory(session);
  }

  async function handleSignOut() {
    setAccountCached(EMPTY_ACCOUNT);
    setHistory([]);
    setActiveTab("brief");
    await supabase.auth.signOut();
  }

  function handleUpgrade() {
    if (!user) { setShowAuth(true); return; }
    setShowPricing(true);
  }

  async function startCheckout(plan, quantity = 1) {
    if (!user) { setShowAuth(true); return; }
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${API}/create-checkout-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ plan, quantity }),
      });
      const body = await res.json();
      if (body.checkout_url) window.location.href = body.checkout_url;
    } catch (e) {
      console.error("Checkout error:", e);
    }
  }

  const isPaid = account.is_admin || account.is_subscriber;

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
          <div className="flex items-center gap-3">
            <img
              src="/prism-logo.png"
              alt="Prism logo"
              width="52"
              height="52"
              className="shrink-0"
              style={{ filter: "drop-shadow(0 0 14px rgba(168,85,247,0.55))" }}
            />
            <div>
              <h1 className="text-3xl sm:text-4xl"
                style={{ fontFamily: "'Cinzel', serif", fontWeight: 500, letterSpacing: "0.18em", color: "#A855F7", textShadow: "0 0 28px rgba(168,85,247,0.6)", textTransform: "uppercase" }}>
                Prism
              </h1>
              <p className="text-sm mt-1" style={{ color: "#475569" }}>Investment intelligence, instantly.</p>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-1">
            {user ? (
              <>
                {!isPaid && (
                  <button onClick={handleUpgrade}
                    className="text-xs font-semibold px-3 py-2 rounded-lg cursor-pointer transition-all duration-200"
                    style={{ background: "rgba(168,85,247,0.18)", border: "1px solid rgba(168,85,247,0.4)", color: "#A855F7" }}
                    onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.28)"}
                    onMouseLeave={e => e.currentTarget.style.background = "rgba(168,85,247,0.18)"}>
                    {account.credits > 0 ? `${account.credits} credits` : "Upgrade"}
                  </button>
                )}
                <button onClick={handleSignOut}
                  className="text-xs px-3 py-2 rounded-lg cursor-pointer transition-all duration-200"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#4E6278" }}
                  onMouseEnter={e => e.currentTarget.style.color = "#64748B"}
                  onMouseLeave={e => e.currentTarget.style.color = "#4E6278"}>
                  {user.email?.split("@")[0]}
                  {account.is_subscriber && <span style={{ color: "#A855F7", marginLeft: 6 }}>Pro</span>}
                  {account.is_admin && <span style={{ color: "#FCD34D", marginLeft: 6 }}>Admin</span>}
                  {"  ·  Sign Out"}
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
        <div className="relative z-20 animate-fade-in-up" style={{ animationDelay: "0.08s" }}>
          <SearchBar onSubmit={handleSearch} loading={loading} initialValue={ticker} />
        </div>

        {/* Body */}
        <div className="relative z-10 mt-6 pb-12">
          {loading && <LoadingState ticker={ticker} />}
          {error && <ErrorState ticker={ticker} message={error} />}

          {!loading && !error && (data || user) && (
            <div className="flex flex-col gap-4">
              {/* Tab nav */}
              <div className="flex items-center gap-1" style={{ borderBottom: "1px solid rgba(168,85,247,0.15)", paddingBottom: 0 }}>
                {[
                  { id: "brief", label: "Brief" },
                  { id: "research", label: "Deep Research" },
                  ...(user ? [{ id: "history", label: "History" }] : []),
                ].map(tab => (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                    className="text-xs font-semibold uppercase tracking-widest px-4 py-2.5 cursor-pointer transition-all"
                    style={{
                      background: "none", border: "none",
                      borderBottom: activeTab === tab.id ? "2px solid #A855F7" : "2px solid transparent",
                      color: activeTab === tab.id ? "#A855F7" : "#3D5068",
                      fontFamily: "'Space Grotesk', sans-serif",
                      marginBottom: -1,
                    }}>
                    {tab.label}
                  </button>
                ))}

                {user && (
                  <span className="ml-auto text-xs px-2" style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
                    {account.is_admin ? "Unlimited"
                      : account.is_subscriber ? "Pro · Unlimited"
                      : <>
                          <span style={{ color: "#A855F7", fontWeight: 600 }}>{account.credits}</span>
                          {` credit${account.credits === 1 ? "" : "s"}`}
                          {account.free_research_available && " · 1 free this week"}
                        </>}
                  </span>
                )}
              </div>

              {/* Tab: Brief */}
              <div style={{ display: activeTab === "brief" ? "block" : "none" }}>
                {data ? (
                  <div className="flex flex-col lg:flex-row lg:items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <BriefCard data={data} />
                    </div>
                    <div className="lg:w-[400px] xl:w-[440px] shrink-0 lg:sticky lg:top-6">
                      <LeftPanel data={data} apiBase={API} user={user} onUpgrade={handleUpgrade} onOpenResearch={() => setActiveTab("research")} />
                    </div>
                  </div>
                ) : (
                  <EmptyTab text="Search a ticker above to see its brief." />
                )}
              </div>

              {/* Tab: Deep Research */}
              <div style={{ display: activeTab === "research" ? "block" : "none" }}>
                {data ? (
                  <ResearchPanel
                    ticker={data.ticker}
                    user={user}
                    account={account}
                    canRun={canRunResearch}
                    hasHistory={history.some(h => h.ticker === data.ticker)}
                    apiBase={API}
                    onUpgrade={handleUpgrade}
                    onRunComplete={refreshAfterRun}
                  />
                ) : (
                  <EmptyTab text="Search a ticker above, then run Deep Research." />
                )}
              </div>

              {/* Tab: History */}
              {user && (
                <div style={{ display: activeTab === "history" ? "block" : "none" }}>
                  <HistorySidebar items={history} activeTicker={data?.ticker} onSelect={openFromHistory} />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer disclaimer */}
        <footer className="text-center pb-6" style={{ color: "#3D5068" }}>
          <p className="text-xs">
            Prism is for informational purposes only, not financial advice.
            Investing involves risk, including loss of principal. Use at your own risk; verify independently before making any investment decision.
          </p>
          <p className="text-xs mt-2">
            <a href="/terms.html" style={{ color: "#4E6278", textDecoration: "underline" }}>Terms of Service</a>
            <span className="mx-2">·</span>
            <a href="/privacy.html" style={{ color: "#4E6278", textDecoration: "underline" }}>Privacy Policy</a>
          </p>
        </footer>
      </div>

      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      {showPricing && <PricingModal account={account} onClose={() => setShowPricing(false)} onCheckout={startCheckout} />}
      <Analytics />
    </div>
  );
}
