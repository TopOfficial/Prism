// Peer comparison table — real fetched data (FMP), not model output.

function fmtMc(v) {
  if (v == null) return "—";
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  return `$${(v / 1e6).toFixed(0)}M`;
}

const num = v => (v == null ? "—" : v);

export default function ComparablesTable({ comparables }) {
  if (!comparables?.peers?.length) return null;
  const rows = [{ ...comparables.subject, _subject: true }, ...comparables.peers];

  return (
    <div className="mb-4">
      <h4 className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
        Comparable Companies
        <span className="ml-2 normal-case tracking-normal font-normal" style={{ color: "#3D5068" }}>
          live data
        </span>
      </h4>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, fontFamily: "'Fira Code', monospace" }}>
          <thead style={{ borderBottom: "1px solid rgba(168,85,247,0.3)" }}>
            <tr>
              {["Ticker", "Company", "Mkt Cap", "P/E", "P/S", "EV/EBITDA"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "#A855F7", fontSize: 12, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.ticker} style={r._subject ? { background: "rgba(168,85,247,0.07)" } : undefined}>
                <td style={{ padding: "7px 12px", color: r._subject ? "#A855F7" : "#E2E8F0", fontWeight: 700, borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{r.ticker}</td>
                <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)", fontFamily: "'Space Grotesk', sans-serif" }}>{r.name || "—"}</td>
                <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{fmtMc(r.market_cap)}</td>
                <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{num(r.pe)}</td>
                <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{num(r.ps)}</td>
                <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{num(r.ev_ebitda)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
