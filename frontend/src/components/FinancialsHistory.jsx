const fmtB = (n) => {
  if (n == null) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${(n / 1e12).toFixed(1)}T`;
  if (abs >= 1e9)  return `${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6)  return `${(n / 1e6).toFixed(1)}M`;
  return n.toFixed(0);
};
const fmtPct = (n) => (n == null ? "—" : `${n.toFixed(1)}%`);

const PERIODS = [
  { key: "fy_minus_2", label: "FY-2" },
  { key: "fy_minus_1", label: "FY-1" },
  { key: "fy_current", label: "FY"   },
  { key: "ttm",        label: "TTM"  },
];

const ROWS = [
  { label: "Revenue",    fn: (p) => fmtB(p?.revenue) },
  { label: "Gross Mgn", fn: (p) => fmtPct(p?.gross_margin_pct) },
  { label: "Op. Mgn",   fn: (p) => fmtPct(p?.operating_margin_pct) },
  { label: "EBITDA",    fn: (p) => fmtB(p?.ebitda) },
  { label: "FCF",       fn: (p) => fmtB(p?.fcf) },
];

export default function FinancialsHistory({ fh }) {
  if (!fh) return null;

  return (
    <div className="overflow-x-auto -mx-1 px-1">
      <table className="w-full text-xs min-w-[300px]">
        <thead>
          <tr>
            <th className="text-left py-2 pr-3 font-normal" style={{ color: "#3D5068", fontFamily: "'Inter', sans-serif" }}>
              Metric
            </th>
            {PERIODS.map((p) => (
              <th
                key={p.key}
                className="text-right py-2 px-2 font-semibold"
                style={{
                  color: p.key === "ttm" ? "#FCD34D" : "#38BDF8",
                  fontFamily: "'Space Grotesk', sans-serif",
                  textShadow: p.key === "ttm" ? "0 0 8px rgba(252,211,77,0.5)" : "0 0 8px rgba(56,189,248,0.4)",
                }}
              >
                {p.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr
              key={row.label}
              className="transition-colors duration-150"
              style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}
              onMouseEnter={e => e.currentTarget.style.background = "rgba(56,189,248,0.04)"}
              onMouseLeave={e => e.currentTarget.style.background = "transparent"}
            >
              <td className="py-2.5 pr-3" style={{ color: "#4E6278", fontFamily: "'Inter', sans-serif" }}>
                {row.label}
              </td>
              {PERIODS.map((p) => {
                const val = row.fn(fh[p.key]);
                const isTtm = p.key === "ttm";
                const allDash = PERIODS.every(pp => row.fn(fh[pp.key]) === "—");
                return (
                  <td
                    key={p.key}
                    className="py-2.5 px-2 text-right"
                    style={{
                      color: val === "—" ? "#2D3D50" : isTtm ? "#FCD34D" : "#CBD5E1",
                      fontFamily: "'Fira Code', monospace",
                      opacity: allDash ? 0.4 : 1,
                    }}
                  >
                    {val}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
