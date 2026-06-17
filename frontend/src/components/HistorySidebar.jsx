function fmtDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "";
  }
}

// Full-width list shown under the "History" tab. Each row opens that ticker's saved report.
export default function HistorySidebar({ items, activeTicker, onSelect }) {
  if (!items || items.length === 0) {
    return (
      <div className="glass-card p-10 text-center animate-fade-in-up" style={{ color: "#3D5068", fontSize: 14 }}>
        No analyses yet — run Deep Research on any ticker and it'll be saved here.
      </div>
    );
  }

  return (
    <div className="glass-card p-2 animate-fade-in-up">
      <div className="flex flex-col">
        {items.map((it) => {
          const active = it.ticker === activeTicker;
          return (
            <button key={it.ticker} onClick={() => onSelect(it.ticker)}
              className="flex items-center gap-4 text-left rounded-lg px-4 py-3 cursor-pointer transition-all"
              style={{ background: active ? "rgba(168,85,247,0.10)" : "transparent" }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = "rgba(168,85,247,0.06)"; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = "transparent"; }}>
              <span style={{ fontFamily: "'Fira Code', monospace", color: "#A855F7", fontWeight: 600, fontSize: 14, minWidth: 68 }}>
                {it.ticker}
              </span>
              <span className="flex-1 truncate" style={{ color: "#94A3B8", fontSize: 13 }}>
                {it.company_name || ""}
              </span>
              <span className="shrink-0" style={{ color: "#3D5068", fontSize: 12 }}>
                {fmtDate(it.created_at)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
