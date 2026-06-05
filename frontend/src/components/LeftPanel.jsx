import QualityScores from "./QualityScores";
import FeedbackWidget from "./FeedbackWidget";

const fmtN = (n, d = 2) => (n == null ? "—" : n.toFixed(d));

const VC = {
  UNDERVALUED: { bg: "rgba(52,211,153,0.07)", border: "rgba(52,211,153,0.4)", label: "#34D399", glow: "0 0 40px rgba(52,211,153,0.18)", badge: "rgba(52,211,153,0.15)" },
  OVERVALUED:  { bg: "rgba(248,113,113,0.07)", border: "rgba(248,113,113,0.4)", label: "#F87171", glow: "0 0 40px rgba(248,113,113,0.18)", badge: "rgba(248,113,113,0.15)" },
  "FAIR VALUE":{ bg: "rgba(252,211,77,0.06)",  border: "rgba(252,211,77,0.35)", label: "#FCD34D", glow: "0 0 40px rgba(252,211,77,0.14)", badge: "rgba(252,211,77,0.14)"  },
};

function SectionTitle({ children, accent = "purple" }) {
  const c = accent === "yellow" ? "#FCD34D" : "#A855F7";
  return (
    <div className="flex items-center gap-2 mb-3.5">
      <div style={{ width: 3, height: 14, borderRadius: 9, background: c, boxShadow: `0 0 8px ${c}` }} />
      <h3 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
        {children}
      </h3>
    </div>
  );
}

export default function LeftPanel({ data, apiBase }) {
  const v  = data.verdict;
  const vc = VC[v?.label] || VC["FAIR VALUE"];

  return (
    <div className="flex flex-col gap-4">

      {/* ── Verdict ── */}
      {v && (
        <div
          className="animate-fade-in-up rounded-2xl p-5"
          style={{ background: vc.bg, border: `1px solid ${vc.border}`, boxShadow: vc.glow, animationDelay: "0.05s" }}
        >
          <div className="flex items-center gap-3 mb-3">
            <span
              className="text-sm font-bold px-3 py-1 rounded-full"
              style={{ background: vc.badge, color: vc.label, border: `1px solid ${vc.border}`, textShadow: `0 0 12px ${vc.label}90`, fontFamily: "'Space Grotesk', sans-serif" }}
            >
              {v.label}
            </span>
          </div>
          <p className="text-sm font-semibold mb-4 leading-relaxed" style={{ color: vc.label }}>{v.reason}</p>
          <div className="flex flex-col gap-2.5">
            <div className="rounded-xl p-3.5" style={{ background: "rgba(52,211,153,0.07)", border: "1px solid rgba(52,211,153,0.2)" }}>
              <p className="text-xs font-semibold mb-1.5" style={{ color: "#34D399" }}>Bull Case</p>
              <p className="text-sm leading-relaxed" style={{ color: "#A7F3D0" }}>{v.bull_case}</p>
            </div>
            <div className="rounded-xl p-3.5" style={{ background: "rgba(248,113,113,0.07)", border: "1px solid rgba(248,113,113,0.2)" }}>
              <p className="text-xs font-semibold mb-1.5" style={{ color: "#F87171" }}>Bear Case</p>
              <p className="text-sm leading-relaxed" style={{ color: "#FECACA" }}>{v.bear_case}</p>
            </div>
          </div>

          {/* Feedback */}
          <div className="mt-4">
            <FeedbackWidget ticker={data.ticker} verdict={v.label} apiBase={apiBase} />
          </div>
        </div>
      )}

      {/* ── Quality Scores ── */}
      {data.quality_scores && (
        <div
          className="animate-fade-in-up glass-card p-5"
          style={{ animationDelay: "0.12s" }}
        >
          <SectionTitle accent="purple">Quality Score</SectionTitle>
          <QualityScores scores={data.quality_scores} />
        </div>
      )}

      {/* ── Valuation ── */}
      <div className="animate-fade-in-up glass-card p-5" style={{ animationDelay: "0.18s" }}>
        <SectionTitle accent="yellow">Valuation</SectionTitle>
        <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.06)" }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <th className="text-left px-4 py-2.5 text-xs font-normal" style={{ color: "#3D5068" }}>Metric</th>
                <th className="text-right px-4 py-2.5 text-xs font-normal" style={{ color: "#3D5068" }}>Value</th>
                {data.valuation?.sector_pe != null && (
                  <th className="text-right px-4 py-2.5 text-xs font-semibold" style={{ color: "#FCD34D" }}>
                    vs Sector {fmtN(data.valuation.sector_pe)}
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {[["P/E", data.valuation?.pe], ["P/B", data.valuation?.pb], ["P/S", data.valuation?.ps], ["EV/EBITDA", data.valuation?.ev_ebitda]].map(([label, val]) => (
                <tr key={label} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.04)"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <td className="px-4 py-2.5 text-sm" style={{ color: "#64748B" }}>{label}</td>
                  <td className="px-4 py-2.5 text-right font-semibold text-white" style={{ fontFamily: "'Fira Code', monospace" }}>{fmtN(val)}</td>
                  {data.valuation?.sector_pe != null && <td />}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── News ── */}
      {data.news?.length > 0 && (
        <div className="animate-fade-in-up glass-card p-5" style={{ animationDelay: "0.24s" }}>
          <SectionTitle>Recent News</SectionTitle>
          <div>
            {data.news.map((item, i) => (
              <div key={i} className="flex gap-3 py-2.5 px-2 -mx-2 rounded-lg"
                style={{ borderBottom: i < data.news.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none", transition: "background 0.15s" }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.04)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                <div style={{ width: 2, borderRadius: 9, flexShrink: 0, marginTop: 3, background: "#A855F7", opacity: 0.4 }} />
                <div className="min-w-0">
                  <a href={item.url} target="_blank" rel="noopener noreferrer"
                    className="text-xs leading-snug block"
                    style={{ color: "#64748B", transition: "color 0.15s" }}
                    onMouseEnter={e => e.currentTarget.style.color = "#A855F7"}
                    onMouseLeave={e => e.currentTarget.style.color = "#64748B"}>
                    {item.title}
                  </a>
                  {item.published && <p className="text-xs mt-0.5" style={{ color: "#2D3D50" }}>{item.published}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
