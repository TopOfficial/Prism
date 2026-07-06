// Watchlist tab: watched tickers + how alerts work. Rows load the ticker on click.

export default function WatchlistTab({ items, limit, activeTicker, onSelect, onRemove, onUpgrade }) {
  const atLimit = limit != null && items.length >= limit;

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
