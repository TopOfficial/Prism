function fmtDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "";
  }
}

export default function HistorySidebar({ items, activeTicker, onSelect }) {
  return (
    <div className="glass-card p-4 lg:sticky lg:top-6 animate-fade-in-up">
      <div className="flex items-center gap-2 mb-3.5">
        <div style={{ width: 3, height: 14, borderRadius: 9, background: "#A855F7", boxShadow: "0 0 8px #A855F7" }} />
        <h3 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
          History
        </h3>
      </div>

      <div className="flex flex-col gap-1">
        {items.map((it) => {
          const active = it.ticker === activeTicker;
          return (
            <button key={it.ticker} onClick={() => onSelect(it.ticker)}
              className="text-left rounded-lg px-3 py-2 cursor-pointer transition-all"
              style={{
                background: active ? "rgba(168,85,247,0.14)" : "transparent",
                border: `1px solid ${active ? "rgba(168,85,247,0.3)" : "transparent"}`,
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = "rgba(168,85,247,0.06)"; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = "transparent"; }}>
              <div style={{ fontFamily: "'Fira Code', monospace", color: "#A855F7", fontSize: 13, fontWeight: 600 }}>
                {it.ticker}
              </div>
              {it.company_name && (
                <div className="truncate" style={{ color: "#64748B", fontSize: 11 }}>{it.company_name}</div>
              )}
              <div style={{ color: "#2D3D50", fontSize: 10, marginTop: 1 }}>{fmtDate(it.created_at)}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
