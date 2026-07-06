import { useState, useEffect } from "react";

// Today's market briefing on the empty homepage — same daily cached content
// for everyone, so this fetch is cheap for the backend.
export default function MarketNews({ apiBase }) {
  const [news, setNews] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase}/market-news`);
        if (!res.ok) throw new Error();
        const body = await res.json();
        if (!cancelled) setNews(body);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => { cancelled = true; };
  }, [apiBase]);

  if (failed) return null; // homepage just shows the search bar, as before
  if (!news) return null;  // no skeleton — appears when ready

  const dateLabel = new Date(`${news.date}T12:00:00`).toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric",
  });

  return (
    <div className="animate-fade-in-up rounded-2xl p-5 mt-6"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(168,85,247,0.18)" }}>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <div style={{ width: 3, height: 14, borderRadius: 9, background: "#A855F7", boxShadow: "0 0 8px #A855F7" }} />
          <h3 className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
            Today&apos;s Market
          </h3>
        </div>
        <span style={{ fontSize: 12, color: "#3D5068" }}>{dateLabel}</span>
      </div>

      {/* Index strip */}
      {news.indexes?.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {news.indexes.map(ix => (
            <div key={ix.symbol} className="px-3 py-2 rounded-xl"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
              <div style={{ fontSize: 11, color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>{ix.label}</div>
              <div className="flex items-baseline gap-2">
                <span style={{ fontSize: 14, fontWeight: 700, color: "#E2E8F0", fontFamily: "'Fira Code', monospace" }}>
                  {ix.price != null ? ix.price.toLocaleString() : "—"}
                </span>
                {ix.change_pct != null && (
                  <span style={{ fontSize: 12, fontWeight: 600, color: ix.change_pct >= 0 ? "#34D399" : "#F87171" }}>
                    {ix.change_pct >= 0 ? "+" : ""}{ix.change_pct}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* AI briefing */}
      {news.briefing && (
        <p className="text-sm mb-4" style={{ color: "#94A3B8", lineHeight: 1.7 }}>{news.briefing}</p>
      )}

      {/* Headlines */}
      {news.headlines?.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }} className="flex flex-col gap-1.5">
          {news.headlines.slice(0, 5).map((h, i) => (
            <li key={i}>
              <a href={h.url} target="_blank" rel="noopener noreferrer"
                className="text-xs transition-colors"
                style={{ color: "#64748B", textDecoration: "none" }}
                onMouseEnter={e => e.currentTarget.style.color = "#A855F7"}
                onMouseLeave={e => e.currentTarget.style.color = "#64748B"}>
                › {h.title}{h.source ? ` — ${h.source}` : ""}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
