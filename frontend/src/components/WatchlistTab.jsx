import { useState, useEffect } from "react";
import { supabase } from "../lib/supabase";

// Watchlist tab: watched tickers + upcoming catalysts + how alerts work.

export default function WatchlistTab({ items, limit, activeTicker, onSelect, onRemove, onUpgrade, apiBase }) {
  const atLimit = limit != null && items.length >= limit;
  const [catalysts, setCatalysts] = useState([]);

  useEffect(() => {
    let cancelled = false;
    if (!items.length) { setCatalysts([]); return; }
    (async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || cancelled) return;
        const res = await fetch(`${apiBase}/catalysts`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (!res.ok || cancelled) return;
        const d = await res.json();
        setCatalysts(d.items || []);
      } catch { /* section just stays empty */ }
    })();
    return () => { cancelled = true; };
  }, [items, apiBase]);

  return (
    <div className="glass-card animate-fade-in-up rounded-2xl overflow-hidden"
      style={{ background: "rgba(168,85,247,0.04)", border: "1px solid rgba(168,85,247,0.18)" }}>
      <div className="flex items-center justify-between px-5 py-4"
        style={{ borderBottom: "1px solid rgba(168,85,247,0.15)" }}>
        <div className="flex items-center gap-3">
          <div style={{ width: 3, height: 14, borderRadius: 9, background: "#A855F7", boxShadow: "0 0 8px #A855F7" }} />
          <h3 className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
            Watchlist
          </h3>
        </div>
        <span style={{ fontSize: 11, color: "#3D5068", fontFamily: "'Space Grotesk', sans-serif" }}>
          {limit == null ? `${items.length} tickers · unlimited` : `${items.length}/${limit} tickers`}
        </span>
      </div>

      <div className="px-5 py-4">
        <p className="text-xs mb-4" style={{ color: "#4E6278", lineHeight: 1.6 }}>
          We check your tickers daily and email you <span style={{ color: "#94A3B8" }}>only when something
          material happens</span> — earnings released, or a move of 5%+ since the last check. No noise.
        </p>

        {items.length === 0 && (
          <p className="text-sm py-4 text-center" style={{ color: "#3D5068" }}>
            Nothing watched yet — search a ticker and hit ☆ Watch.
          </p>
        )}

        <div className="flex flex-col gap-1">
          {items.map(item => (
            <div key={item.ticker}
              className="flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-all"
              style={{
                background: activeTicker === item.ticker ? "rgba(168,85,247,0.1)" : "transparent",
                border: "1px solid " + (activeTicker === item.ticker ? "rgba(168,85,247,0.3)" : "transparent"),
              }}
              onClick={() => onSelect(item.ticker)}
              onMouseEnter={e => { if (activeTicker !== item.ticker) e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
              onMouseLeave={e => { if (activeTicker !== item.ticker) e.currentTarget.style.background = "transparent"; }}>
              <div className="min-w-0">
                <span className="text-sm font-bold" style={{ color: "#E2E8F0", fontFamily: "'Fira Code', monospace" }}>
                  {item.ticker}
                </span>
                {item.company_name && (
                  <span className="text-xs ml-2 truncate" style={{ color: "#4E6278" }}>{item.company_name}</span>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span style={{ fontSize: 11, color: "#3D5068" }}>
                  {item.added_at && new Date(item.added_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </span>
                <button aria-label={`Remove ${item.ticker}`}
                  onClick={e => { e.stopPropagation(); onRemove(item.ticker); }}
                  className="cursor-pointer"
                  style={{ background: "none", border: "none", color: "#3D5068", fontSize: 14, padding: "2px 6px" }}
                  onMouseEnter={e => e.currentTarget.style.color = "#F87171"}
                  onMouseLeave={e => e.currentTarget.style.color = "#3D5068"}>
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>

        {catalysts.length > 0 && (
          <div className="mt-5 pt-4" style={{ borderTop: "1px solid rgba(168,85,247,0.12)" }}>
            <h4 className="text-xs font-semibold uppercase tracking-widest mb-3"
              style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
              Upcoming Catalysts
            </h4>
            <div className="flex flex-col gap-1.5">
              {catalysts.map(c => (
                <div key={c.ticker} className="flex items-center gap-3 flex-wrap text-xs px-3 py-2 rounded-xl cursor-pointer"
                  style={{ background: "rgba(255,255,255,0.02)" }}
                  onClick={() => onSelect(c.ticker)}>
                  <span className="font-bold" style={{ color: "#E2E8F0", fontFamily: "'Fira Code', monospace" }}>{c.ticker}</span>
                  {c.next_earnings && (
                    <span style={{ color: "#A855F7" }}>
                      Earnings {c.next_earnings.date}
                      {c.next_earnings.eps_estimate != null && (
                        <span style={{ color: "#64748B" }}> · est EPS {c.next_earnings.eps_estimate}</span>
                      )}
                    </span>
                  )}
                  {c.next_dividend && (
                    <span style={{ color: "#34D399" }}>
                      Ex-div {c.next_dividend.ex_date}
                      {c.next_dividend.amount != null && <span style={{ color: "#64748B" }}> · ${c.next_dividend.amount}</span>}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {atLimit && (
          <div className="mt-4 px-4 py-3 rounded-xl flex items-center justify-between flex-wrap gap-2"
            style={{ background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.22)" }}>
            <span className="text-xs" style={{ color: "#94A3B8" }}>
              Free plan watches {limit} tickers. Subscribe for an unlimited watchlist.
            </span>
            <button onClick={onUpgrade}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg cursor-pointer"
              style={{ background: "#A855F7", border: "none", color: "#fff" }}>
              Upgrade
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
