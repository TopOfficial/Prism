import { useState, useEffect, useCallback } from "react";
import { supabase } from "../lib/supabase";

const fmtMoney = v => v == null ? "—" : `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

export default function PortfolioTab({ apiBase, onUpgrade, onSelect }) {
  const [text, setText] = useState("");
  const [data, setData] = useState(null);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [assessing, setAssessing] = useState(false);
  const [editing, setEditing] = useState(false);

  const load = useCallback(async (withAssess = false) => {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) return;
    if (withAssess) setAssessing(true);
    try {
      const res = await fetch(`${apiBase}/portfolio${withAssess ? "?assess=1" : ""}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });
      if (res.status === 402) { onUpgrade(); return; }
      if (res.ok) {
        const d = await res.json();
        setData(prev => withAssess && !d.assessment ? { ...d, assessment: prev?.assessment } : d);
      }
    } catch { /* keep current state */ } finally {
      setAssessing(false);
    }
  }, [apiBase, onUpgrade]);

  useEffect(() => { load(); }, [load]);

  async function saveHoldings() {
    setLoading(true);
    setErrors([]);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${apiBase}/portfolio`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ text }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErrors(body.detail?.errors || ["Couldn't save — check the format."]);
        return;
      }
      setErrors(body.errors || []);
      setEditing(false);
      await load();
    } catch {
      setErrors(["Network error — try again."]);
    } finally {
      setLoading(false);
    }
  }

  const hasHoldings = data?.holdings?.length > 0;
  const showInput = editing || !hasHoldings;

  return (
    <div className="animate-fade-in-up rounded-2xl overflow-hidden"
      style={{ background: "rgba(168,85,247,0.04)", border: "1px solid rgba(168,85,247,0.18)" }}>
      <div className="flex items-center justify-between px-5 py-4"
        style={{ borderBottom: "1px solid rgba(168,85,247,0.15)" }}>
        <div className="flex items-center gap-3">
          <div style={{ width: 3, height: 14, borderRadius: 9, background: "#A855F7", boxShadow: "0 0 8px #A855F7" }} />
          <h3 className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
            Portfolio
          </h3>
        </div>
        {hasHoldings && !editing && (
          <button onClick={() => setEditing(true)}
            style={{ fontSize: 12, color: "#3D5068", background: "none", border: "none", cursor: "pointer" }}>
            Edit holdings
          </button>
        )}
      </div>

      <div className="px-5 py-4">
        {showInput && (
          <div className="mb-4">
            <p className="text-xs mb-2" style={{ color: "#4E6278", lineHeight: 1.6 }}>
              One holding per line: <code style={{ color: "#94A3B8" }}>TICKER, shares</code> or{" "}
              <code style={{ color: "#94A3B8" }}>TICKER, shares, cost basis</code>
            </p>
            <textarea value={text} onChange={e => setText(e.target.value)}
              placeholder={"AAPL, 10, 150\nNVDA, 4\nKO, 25, 58.20"}
              rows={6}
              className="w-full text-sm px-4 py-3 rounded-xl"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#E2E8F0", outline: "none", fontFamily: "'Fira Code', monospace", resize: "vertical" }} />
            {errors.length > 0 && (
              <div className="mt-2">
                {errors.map((e, i) => (
                  <p key={i} className="text-xs" style={{ color: "#F87171" }}>{e}</p>
                ))}
              </div>
            )}
            <div className="flex gap-2 mt-2">
              <button onClick={saveHoldings} disabled={loading || !text.trim()}
                className="text-sm font-semibold px-4 py-2 rounded-xl cursor-pointer"
                style={{ background: loading || !text.trim() ? "rgba(168,85,247,0.25)" : "#A855F7", border: "none", color: "#fff" }}>
                {loading ? "Analyzing…" : "Save & Analyze"}
              </button>
              {editing && (
                <button onClick={() => { setEditing(false); setErrors([]); }}
                  style={{ fontSize: 12, color: "#3D5068", background: "none", border: "none", cursor: "pointer" }}>
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}

        {hasHoldings && !showInput && (
          <>
            {/* Totals strip */}
            <div className="flex flex-wrap gap-2 mb-4">
              {[
                ["Total value", fmtMoney(data.totals.value)],
                ["Weighted P/E", data.totals.weighted_pe ?? "—"],
                ["Top position", `${data.totals.top_weight_pct}%`],
                ["Concentration (HHI)", data.totals.hhi],
              ].map(([label, val]) => (
                <div key={label} className="px-3 py-2 rounded-xl"
                  style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                  <div style={{ fontSize: 11, color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>{label}</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "#E2E8F0", fontFamily: "'Fira Code', monospace" }}>{val}</div>
                </div>
              ))}
            </div>

            {/* Holdings table */}
            <div style={{ overflowX: "auto" }} className="mb-4">
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, fontFamily: "'Fira Code', monospace" }}>
                <thead style={{ borderBottom: "1px solid rgba(168,85,247,0.3)" }}>
                  <tr>
                    {["Ticker", "Value", "Weight", "P/E", "Gain"].map(h => (
                      <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "#A855F7", fontSize: 12, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif", textTransform: "uppercase" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.holdings.map(h => (
                    <tr key={h.ticker} onClick={() => onSelect(h.ticker)} style={{ cursor: "pointer" }}>
                      <td style={{ padding: "7px 12px", color: "#E2E8F0", fontWeight: 700, borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{h.ticker}</td>
                      <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{fmtMoney(h.value)}</td>
                      <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{h.weight_pct}%</td>
                      <td style={{ padding: "7px 12px", color: "#94A3B8", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{h.pe ?? "—"}</td>
                      <td style={{ padding: "7px 12px", color: h.gain_pct == null ? "#3D5068" : h.gain_pct >= 0 ? "#34D399" : "#F87171", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                        {h.gain_pct == null ? "—" : `${h.gain_pct >= 0 ? "+" : ""}${h.gain_pct}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data.unpriced?.length > 0 && (
              <p className="text-xs mb-4" style={{ color: "#FCD34D" }}>
                No price data for: {data.unpriced.join(", ")} — excluded from the analysis.
              </p>
            )}

            {/* Sector bars */}
            <div className="mb-5">
              {data.sectors.map(s => (
                <div key={s.sector} className="flex items-center gap-3 mb-1.5">
                  <span className="text-xs shrink-0" style={{ width: 150, color: "#94A3B8", fontFamily: "'Space Grotesk', sans-serif" }}>{s.sector}</span>
                  <div className="flex-1 rounded-full overflow-hidden" style={{ height: 8, background: "rgba(255,255,255,0.07)" }}>
                    <div className="h-full rounded-full" style={{ width: `${s.weight_pct}%`, background: "#A855F7" }} />
                  </div>
                  <span className="text-xs shrink-0" style={{ width: 42, color: "#64748B", fontFamily: "'Fira Code', monospace", textAlign: "right" }}>{s.weight_pct}%</span>
                </div>
              ))}
            </div>

            {/* AI assessment */}
            {data.assessment ? (
              <div className="px-4 py-3 rounded-xl" style={{ background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.22)" }}>
                <div className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: "#A855F7", fontFamily: "'Space Grotesk', sans-serif" }}>AI Assessment</div>
                <p className="text-sm" style={{ color: "#94A3B8", lineHeight: 1.7, whiteSpace: "pre-wrap", margin: 0 }}>{data.assessment}</p>
              </div>
            ) : data.can_assess ? (
              <button onClick={() => load(true)} disabled={assessing}
                className="text-sm font-semibold px-4 py-2 rounded-xl cursor-pointer"
                style={{ background: "rgba(168,85,247,0.18)", border: "1px solid rgba(168,85,247,0.4)", color: "#A855F7" }}>
                {assessing ? "Assessing…" : "Get AI assessment"}
              </button>
            ) : (
              <div className="px-4 py-3 rounded-xl flex items-center justify-between flex-wrap gap-2"
                style={{ background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.22)" }}>
                <span className="text-xs" style={{ color: "#94A3B8" }}>
                  AI portfolio assessment — risk, overlap, and rebalancing considerations — is a Pro feature.
                </span>
                <button onClick={onUpgrade}
                  className="text-xs font-semibold px-3 py-1.5 rounded-lg cursor-pointer"
                  style={{ background: "#A855F7", border: "none", color: "#fff" }}>
                  Upgrade
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
