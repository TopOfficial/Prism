import FinancialsHistory from "./FinancialsHistory";

const CCY_SYMBOL = {
  USD: "$", THB: "฿", GBP: "£", EUR: "€", JPY: "¥", CNY: "¥", HKD: "HK$",
  INR: "₹", CAD: "C$", AUD: "A$", NZD: "NZ$", KRW: "₩", TWD: "NT$", SGD: "S$",
  CHF: "CHF ", SEK: "kr", NOK: "kr", DKK: "kr", BRL: "R$", MXN: "MX$",
  IDR: "Rp", MYR: "RM", PHP: "₱", ZAR: "R",
};
const sym = (currency) => (currency ? (CCY_SYMBOL[currency.toUpperCase()] || `${currency.toUpperCase()} `) : "$");

const fmtB = (n) => {
  if (n == null) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (abs >= 1e9)  return `${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6)  return `${(n / 1e6).toFixed(2)}M`;
  return new Intl.NumberFormat("en-US").format(n);
};
const fmtPct = (n) => (n == null ? "—" : `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`);
const fmtN   = (n, d = 2) => (n == null ? "—" : n.toFixed(d));

function Section({ children, delay = 0 }) {
  return (
    <div className="animate-fade-in-up" style={{ animationDelay: `${delay}s` }}>
      {children}
    </div>
  );
}

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

function Metric({ label, value, accent }) {
  const valColor   = accent === "purple" ? "#A855F7" : accent === "yellow" ? "#FCD34D" : "#E2E8F0";
  const glowShadow = accent === "purple" ? "0 0 10px rgba(168,85,247,0.4)" : accent === "yellow" ? "0 0 10px rgba(252,211,77,0.4)" : "none";
  return (
    <div
      className="rounded-xl p-3.5 cursor-default"
      style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.06)", transition: "background 0.2s, border-color 0.2s" }}
      onMouseEnter={e => { e.currentTarget.style.background = "rgba(168,85,247,0.05)"; e.currentTarget.style.borderColor = "rgba(168,85,247,0.22)"; }}
      onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.025)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; }}
    >
      <p className="text-xs mb-1" style={{ color: "#3D5068" }}>{label}</p>
      <p style={{ color: valColor, fontFamily: "'Fira Code', monospace", fontWeight: 600, fontSize: 15, textShadow: glowShadow }}>{value}</p>
    </div>
  );
}

function RangeBar({ price, low, high, ccy }) {
  if (price == null || low == null || high == null || high === low) return null;
  const pct = Math.min(100, Math.max(0, ((price - low) / (high - low)) * 100));
  return (
    <div className="mt-4">
      <div className="relative h-1 rounded-full" style={{ background: "rgba(255,255,255,0.07)" }}>
        <div style={{ position: "absolute", left: 0, top: 0, height: "100%", borderRadius: "9999px", width: `${pct}%`, background: "linear-gradient(90deg, rgba(168,85,247,0.3), #A855F7)", transition: "width 1s cubic-bezier(0.34,1.56,0.64,1)" }} />
        <div style={{ position: "absolute", left: `${pct}%`, top: "50%", transform: "translate(-50%,-50%)", width: 12, height: 12, borderRadius: "50%", background: "#A855F7", boxShadow: "0 0 12px rgba(168,85,247,0.9)", border: "2px solid #070B14" }} />
      </div>
      <div className="flex justify-between mt-1.5">
        <span className="text-xs" style={{ color: "#3D5068", fontFamily: "'Fira Code', monospace" }}>{ccy}{fmtN(low)}</span>
        <span className="text-xs" style={{ color: "#3D5068" }}>52-wk range</span>
        <span className="text-xs" style={{ color: "#3D5068", fontFamily: "'Fira Code', monospace" }}>{ccy}{fmtN(high)}</span>
      </div>
    </div>
  );
}

function sentimentColor(s) {
  if (s === "buying")  return { color: "#34D399", bg: "rgba(52,211,153,0.12)",  border: "rgba(52,211,153,0.25)" };
  if (s === "selling") return { color: "#F87171", bg: "rgba(248,113,113,0.12)", border: "rgba(248,113,113,0.25)" };
  return                       { color: "#FCD34D", bg: "rgba(252,211,77,0.12)", border: "rgba(252,211,77,0.25)" };
}

export default function BriefCard({ data }) {
  const isUp = (data.change_pct_1d ?? 0) >= 0;
  const ccy = sym(data.currency);

  return (
    <div className="flex flex-col gap-4">

      {/* ── Company Header ── */}
      <Section delay={0}>
        <div className="glass-card p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="font-bold text-white text-xl truncate" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                  {data.company_name || data.ticker}
                </h2>
                <span className="text-xs px-2 py-0.5 rounded shrink-0" style={{ fontFamily: "'Fira Code', monospace", background: "rgba(168,85,247,0.1)", color: "#A855F7", border: "1px solid rgba(168,85,247,0.28)", textShadow: "0 0 8px rgba(168,85,247,0.5)" }}>
                  {data.ticker}
                </span>
                {data.sector && (
                  <span className="text-xs px-2 py-0.5 rounded shrink-0" style={{ background: "rgba(252,211,77,0.08)", color: "#FCD34D", border: "1px solid rgba(252,211,77,0.22)" }}>
                    {data.sector}
                  </span>
                )}
              </div>
              <p className="text-xs mt-1" style={{ color: "#3D5068" }}>{data.currency}</p>
            </div>
            <div className="text-right shrink-0">
              <p className="font-bold" style={{ fontFamily: "'Fira Code', monospace", fontSize: 30, color: "#F0F4FF", letterSpacing: "-0.02em" }}>
                {ccy}{fmtN(data.price)}
              </p>
              <p className="text-sm font-semibold mt-0.5" style={{ fontFamily: "'Fira Code', monospace", color: isUp ? "#34D399" : "#F87171", textShadow: isUp ? "0 0 10px rgba(52,211,153,0.6)" : "0 0 10px rgba(248,113,113,0.6)" }}>
                {fmtPct(data.change_pct_1d)} today
              </p>
            </div>
          </div>
          <RangeBar price={data.price} low={data.week_52_low} high={data.week_52_high} ccy={ccy} />
          {data.market_cap != null && (
            <p className="text-xs mt-3" style={{ color: "#3D5068" }}>
              Market cap: <span style={{ color: "#64748B" }}>{fmtB(data.market_cap)}</span>
            </p>
          )}
        </div>
      </Section>

      {/* ── Overview ── */}
      <Section delay={0.08}>
        <div className="glass-card p-5">
          <SectionTitle>Overview</SectionTitle>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            <Metric label="Revenue TTM" value={fmtB(data.overview?.revenue_ttm)} />
            <Metric label="EPS TTM"     value={data.overview?.eps_ttm == null ? "—" : `${ccy}${fmtN(data.overview.eps_ttm)}`} />
            <Metric label="Net Margin"  value={data.overview?.net_margin_pct == null ? "—" : `${fmtN(data.overview.net_margin_pct)}%`} />
            <Metric label="FCF TTM"     value={fmtB(data.overview?.fcf_ttm)}       accent="purple" />
            <Metric label="ROIC"        value={data.overview?.roic_ttm == null ? "—" : `${fmtN(data.overview.roic_ttm)}%`} accent="yellow" />
            <Metric label="ROE"         value={data.overview?.roe_ttm  == null ? "—" : `${fmtN(data.overview.roe_ttm)}%`} />
          </div>
        </div>
      </Section>

      {/* ── Financials History ── */}
      {data.financials_history && (
        <Section delay={0.14}>
          <div className="glass-card p-5">
            <SectionTitle accent="yellow">Financials History</SectionTitle>
            <FinancialsHistory fh={data.financials_history} />
          </div>
        </Section>
      )}

      {/* ── Balance Sheet ── */}
      <Section delay={0.2}>
        <div className="glass-card p-5">
          <SectionTitle>Balance Sheet</SectionTitle>
          <div className="grid grid-cols-3 gap-2.5">
            <Metric label="Total Debt" value={fmtB(data.balance_sheet?.total_debt)} />
            <Metric label="Cash"       value={fmtB(data.balance_sheet?.cash)}       accent="purple" />
            <Metric label="D/E Ratio"  value={fmtN(data.balance_sheet?.de_ratio)} />
          </div>
        </div>
      </Section>

      {/* ── Earnings History ── */}
      {data.earnings_history?.length > 0 && (
        <Section delay={0.26}>
          <div className="glass-card p-5">
            <SectionTitle>Earnings History</SectionTitle>
            <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.06)" }}>
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    {["Quarter", "Estimate", "Actual", "Result"].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-xs font-normal" style={{ color: "#3D5068" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.earnings_history.map((row, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
                      onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.04)"}
                      onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                      <td className="px-4 py-2.5 text-xs" style={{ color: "#4E6278", fontFamily: "'Fira Code', monospace" }}>{row.quarter || "—"}</td>
                      <td className="px-4 py-2.5" style={{ color: "#64748B", fontFamily: "'Fira Code', monospace" }}>{row.eps_estimate == null ? "—" : `${ccy}${fmtN(row.eps_estimate)}`}</td>
                      <td className="px-4 py-2.5 font-semibold text-white" style={{ fontFamily: "'Fira Code', monospace" }}>{row.eps_actual == null ? "—" : `${ccy}${fmtN(row.eps_actual)}`}</td>
                      <td className="px-4 py-2.5">
                        {row.beat == null
                          ? <span className="text-xs" style={{ color: "#3D5068" }}>—</span>
                          : row.beat
                            ? <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: "rgba(52,211,153,0.12)", color: "#34D399", border: "1px solid rgba(52,211,153,0.25)" }}>Beat</span>
                            : <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: "rgba(248,113,113,0.12)", color: "#F87171", border: "1px solid rgba(248,113,113,0.25)" }}>Miss</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Section>
      )}

      {/* ── Institutional ── */}
      <Section delay={0.32}>
        <div className="glass-card p-5">
          <SectionTitle>Institutional</SectionTitle>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
            <Metric label="Top Holder"     value={data.institutional?.top_holder || "—"} />
            <Metric label="Institutions %" value={data.institutional?.pct_held_institutions == null ? "—" : `${fmtN(data.institutional.pct_held_institutions)}%`} accent="purple" />
            <Metric label="Short % Float"  value={data.institutional?.short_percent_of_float == null ? "—" : `${fmtN(data.institutional.short_percent_of_float)}%`} />
            <Metric label="Shares Trend"   value={data.institutional?.shares_buyback_trend || "—"} />
          </div>

          {data.institutional?.last_5_insider_transactions?.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#3D5068" }}>Insider Activity</p>
                {data.institutional.insider_sentiment && (() => {
                  const sc = sentimentColor(data.institutional.insider_sentiment);
                  return (
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold capitalize"
                      style={{ background: sc.bg, color: sc.color, border: `1px solid ${sc.border}` }}>
                      {data.institutional.insider_sentiment}
                    </span>
                  );
                })()}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs min-w-[380px]">
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                      {["Date", "Name", "Shares"].map(h => (
                        <th key={h} className="text-left py-2 pr-4 font-normal" style={{ color: "#3D5068" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.institutional.last_5_insider_transactions.map((tx, i) => {
                      return (
                        <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}
                          onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.04)"}
                          onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                          <td className="py-2 pr-4" style={{ color: "#3D5068", fontFamily: "'Fira Code', monospace" }}>{tx.date || "—"}</td>
                          <td className="py-2 pr-4 max-w-[120px] truncate" style={{ color: "#64748B" }}>{tx.name || "—"}</td>
                          <td className="py-2" style={{ color: "#94A3B8", fontFamily: "'Fira Code', monospace" }}>
                            {tx.shares == null ? "—" : new Intl.NumberFormat("en-US", { notation: "compact" }).format(tx.shares)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </Section>

    </div>
  );
}
