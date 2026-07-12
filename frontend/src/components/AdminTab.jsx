import { useState, useEffect, useCallback } from "react";
import { supabase } from "../lib/supabase";

const fmtWhen = ts => {
  if (!ts) return "—";
  const d = new Date(ts);
  if (isNaN(d)) return "—";
  return d.toLocaleString("en-GB", {
    timeZone: "Asia/Bangkok",
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
};

const CHARGE_COLOR = {
  credit: "#A855F7",
  free_weekly: "#34D399",
  unlimited: "#FCD34D",
};

function Stat({ label, value }) {
  return (
    <div className="rounded-xl px-4 py-3"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(168,85,247,0.15)" }}>
      <div className="text-2xl font-semibold" style={{ color: "#E2E8F0", fontFamily: "'Space Grotesk', sans-serif" }}>
        {value ?? "—"}
      </div>
      <div className="text-xs mt-1 uppercase tracking-widest" style={{ color: "#4E6278" }}>{label}</div>
    </div>
  );
}

export default function AdminTab({ apiBase }) {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { setError("Not signed in."); return; }
      const res = await fetch(`${apiBase}/stats`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (!res.ok) { setError(`Stats request failed (${res.status}).`); return; }
      setStats(await res.json());
    } catch {
      setError("Could not reach the API.");
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => { load(); }, [load]);

  if (loading && !stats) return <p className="text-sm py-8" style={{ color: "#4E6278" }}>Loading stats…</p>;
  if (error) return <p className="text-sm py-8" style={{ color: "#F87171" }}>{error}</p>;
  if (!stats) return null;

  const events = stats.recent_research || [];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "#A855F7", fontFamily: "'Space Grotesk', sans-serif" }}>
          Usage — Admin
        </h2>
        <button onClick={load}
          className="text-xs px-3 py-1.5 rounded-lg cursor-pointer transition-all"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#64748B" }}>
          ↻ Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Stat label="Total runs" value={stats.total_runs} />
        <Stat label="Runs · 7d" value={stats.runs_last_7_days} />
        <Stat label="Shared reuse · 7d" value={stats.shared_reuses_7d} />
        <Stat label="Users" value={stats.registered_users} />
        <Stat label="Subscribers" value={stats.subscribers} />
        <Stat label="Credits out" value={stats.credits_outstanding} />
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#4E6278" }}>
          Deep Research log · last {events.length} runs (Bangkok time)
        </h3>
        {events.length === 0 ? (
          <p className="text-sm py-4" style={{ color: "#4E6278" }}>
            No runs logged yet. Events appear here after the next Deep Research run.
          </p>
        ) : (
          <div className="rounded-xl overflow-x-auto"
            style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(168,85,247,0.12)" }}>
            <table className="w-full text-sm" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(168,85,247,0.15)" }}>
                  {["When", "User", "Ticker", "Charge", "Source"].map(h => (
                    <th key={h} className="text-left text-xs uppercase tracking-widest px-4 py-2.5" style={{ color: "#4E6278" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {events.map((e, i) => (
                  <tr key={i} style={{ borderBottom: i < events.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
                    <td className="px-4 py-2.5 whitespace-nowrap" style={{ color: "#64748B" }}>{fmtWhen(e.created_at)}</td>
                    <td className="px-4 py-2.5" style={{ color: "#94A3B8" }}>{e.email || "—"}</td>
                    <td className="px-4 py-2.5 font-semibold" style={{ color: "#E2E8F0" }}>{e.ticker}</td>
                    <td className="px-4 py-2.5" style={{ color: CHARGE_COLOR[e.charge_type] || "#64748B" }}>{e.charge_type}</td>
                    <td className="px-4 py-2.5" style={{ color: e.source === "shared" ? "#34D399" : "#64748B" }}>{e.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {(stats.top_tickers || []).length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#4E6278" }}>Top tickers · all time</h3>
          <div className="flex flex-wrap gap-2">
            {stats.top_tickers.map(t => (
              <span key={t.ticker} className="text-xs px-3 py-1.5 rounded-lg"
                style={{ background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.2)", color: "#94A3B8" }}>
                <span style={{ color: "#E2E8F0", fontWeight: 600 }}>{t.ticker}</span> · {t.runs}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
