import { useEffect } from "react";

const SECTIONS = [
  {
    title: "Header",
    items: [
      { label: "Price / Change",  desc: "Current stock price and today's % change vs yesterday's close." },
      { label: "52-Week Range",   desc: "Bar shows where the current price sits between the 52-week low and high." },
      { label: "Market Cap",      desc: "Total market value of all shares outstanding (price × shares)." },
    ],
  },
  {
    title: "Quality Score",
    items: [
      { label: "Business Quality (1–10)",    desc: "Scored on gross/operating margins and revenue growth. Higher = more durable, profitable business." },
      { label: "Financial Health (1–10)",    desc: "Scored on debt load, FCF, ROE, and leverage. Higher = stronger balance sheet." },
      { label: "Valuation (1–10)",           desc: "Scored on P/E vs sector and P/FCF. Higher = stock looks cheaper vs fundamentals." },
      { label: "Growth Outlook (1–10)",      desc: "Scored on revenue growth and earnings beat/miss trend." },
      { label: "Overall",                    desc: "Simple average of the four dimensions — rough composite quality rating." },
      { label: "Signals",                    desc: "Top 3 rules that most influenced the scores up or down." },
    ],
  },
  {
    title: "Overview",
    items: [
      { label: "Revenue TTM",  desc: "Total revenue over the trailing twelve months." },
      { label: "EPS TTM",      desc: "Earnings Per Share (trailing 12 months) — profit per share." },
      { label: "Net Margin",   desc: "% of revenue left as profit after all expenses. Higher = more efficient." },
      { label: "FCF TTM",      desc: "Free Cash Flow — real cash the business generates after capex." },
      { label: "ROIC",         desc: "Return on Invested Capital. How efficiently invested money turns to profit. Above 15% is strong." },
      { label: "ROE",          desc: "Return on Equity. Profit per dollar of shareholders' equity. Above 15% is good." },
    ],
  },
  {
    title: "Financials History",
    items: [
      { label: "FY-2 / FY-1 / FY / TTM", desc: "Three fiscal years + trailing twelve months — shows trend in revenue, margins, EBITDA, and FCF." },
      { label: "Gross Margin",            desc: "Revenue minus cost of goods, as %. High and stable = pricing power." },
      { label: "Operating Margin",        desc: "Profit from core operations as % of revenue, before interest/taxes." },
      { label: "EBITDA Margin",           desc: "Cash profitability % before accounting adjustments." },
      { label: "FCF (per year)",          desc: "Free cash flow each fiscal year. Consistent positive FCF = healthy business." },
    ],
  },
  {
    title: "Balance Sheet",
    items: [
      { label: "Total Debt",  desc: "All interest-bearing obligations (short + long term)." },
      { label: "Cash",        desc: "Cash and short-term investments — the company's liquidity buffer." },
      { label: "D/E Ratio",   desc: "Debt-to-Equity. Above 2x signals elevated leverage risk." },
    ],
  },
  {
    title: "Valuation",
    items: [
      { label: "P/E",        desc: "Price-to-Earnings. Compare to Sector P/E to judge premium/discount." },
      { label: "P/B",        desc: "Price-to-Book. Below 1 may signal undervaluation." },
      { label: "P/S",        desc: "Price-to-Sales. Useful when there are no earnings yet." },
      { label: "EV/EBITDA",  desc: "Capital-structure-neutral valuation. Below 10x often considered cheap." },
      { label: "Sector P/E", desc: "Industry median P/E — benchmark for premium vs discount." },
    ],
  },
  {
    title: "Earnings History",
    items: [
      { label: "Estimate vs Actual",  desc: "Wall Street consensus EPS vs what the company actually reported." },
      { label: "Beat / Miss",         desc: "Beat = actual ≥ estimate. Consistent beats = strong execution." },
    ],
  },
  {
    title: "Institutional",
    items: [
      { label: "Top Holder",       desc: "The single largest institutional investor by shares held." },
      { label: "Institutions %",   desc: "Portion of shares owned by funds and institutions." },
      { label: "Short % Float",    desc: "% of tradeable shares sold short. Above 10% is elevated." },
      { label: "Shares Trend",     desc: "buyback = shrinking shares (positive). diluting = growing shares (negative)." },
      { label: "Insider Activity", desc: "Recent transactions by executives and directors." },
      { label: "Sentiment",        desc: "Net direction of insider trades in last 90 days." },
    ],
  },
  {
    title: "Verdict",
    items: [
      { label: "UNDERVALUED",  desc: "P/E below 80% of sector P/E and FCF positive — appears cheap vs peers." },
      { label: "OVERVALUED",   desc: "P/E exceeds 130% of sector P/E — appears expensive vs peers." },
      { label: "FAIR VALUE",   desc: "P/E within normal range, or insufficient data for a stronger verdict." },
      { label: "Bull / Bear",  desc: "Strongest supporting metric vs biggest risk flag, from the data." },
    ],
  },
];

export default function HelpModal({ onClose }) {
  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose(); }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center px-4 py-8 sm:py-12 overflow-y-auto"
      style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl p-6 animate-fade-in-up"
        style={{
          background: "rgba(8,12,22,0.97)",
          border: "1px solid rgba(56,189,248,0.22)",
          boxShadow: "0 0 60px rgba(56,189,248,0.1)",
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-bold text-white" style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 18 }}>
            What does each section mean?
          </h2>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-8 h-8 rounded-lg cursor-pointer transition-all duration-200"
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#64748B" }}
            onMouseEnter={e => { e.currentTarget.style.background = "rgba(248,113,113,0.1)"; e.currentTarget.style.color = "#F87171"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.05)"; e.currentTarget.style.color = "#64748B"; }}
            aria-label="Close"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Sections */}
        <div className="space-y-5">
          {SECTIONS.map((section) => (
            <div key={section.title}>
              <div className="flex items-center gap-2 mb-2">
                <div style={{ width: 3, height: 12, borderRadius: 9, background: "#38BDF8", boxShadow: "0 0 6px rgba(56,189,248,0.7)", flexShrink: 0 }} />
                <h3 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#3D5068", fontFamily: "'Space Grotesk', sans-serif" }}>
                  {section.title}
                </h3>
              </div>
              <div className="space-y-1.5 ml-3">
                {section.items.map((item) => (
                  <div
                    key={item.label}
                    className="flex gap-3 rounded-lg px-3 py-2.5"
                    style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}
                  >
                    <span className="text-xs font-semibold shrink-0" style={{ color: "#38BDF8", minWidth: 130, fontFamily: "'Inter', sans-serif" }}>
                      {item.label}
                    </span>
                    <span className="text-xs" style={{ color: "#64748B", lineHeight: 1.6 }}>{item.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <p className="text-xs text-center mt-6" style={{ color: "#1E2D40" }}>
          Data from yfinance · Scores are rule-based, not financial advice · Press Esc to close
        </p>
      </div>
    </div>
  );
}
