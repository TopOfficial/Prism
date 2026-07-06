import { useState } from "react";

// "What if" scenario model — transparent driver math, no black-box DCF:
// implied price = EPS(TTM) × (1+growth)^years × exit P/E.
export default function ScenarioModel({ data }) {
  const eps = data?.overview?.eps_ttm;
  const price = data?.price;
  const currentPe = data?.valuation?.pe;
  const [growth, setGrowth] = useState(15);
  const [years, setYears] = useState(3);
  const [exitPe, setExitPe] = useState(currentPe ? Math.round(currentPe) : 20);

  if (eps == null || eps <= 0 || !price) return null; // needs positive EPS to model

  const futureEps = eps * Math.pow(1 + growth / 100, years);
  const implied = futureEps * exitPe;
  const totalReturn = (implied - price) / price * 100;
  const cagr = (Math.pow(implied / price, 1 / years) - 1) * 100;
  const retColor = totalReturn >= 0 ? "#34D399" : "#F87171";

  const Slider = ({ label, value, set, min, max, step = 1, suffix = "" }) => (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs" style={{ color: "#94A3B8", fontFamily: "'Space Grotesk', sans-serif" }}>{label}</span>
        <span className="text-xs font-bold" style={{ color: "#A855F7", fontFamily: "'Fira Code', monospace" }}>{value}{suffix}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => set(Number(e.target.value))}
        className="w-full" style={{ accentColor: "#A855F7" }} />
    </div>
  );

  return (
    <div className="rounded-2xl p-5 mt-4"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(168,85,247,0.18)" }}>
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
          Scenario Model
        </h4>
        <span style={{ fontSize: 11, color: "#3D5068" }}>EPS × growth × exit multiple</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-x-6">
        <Slider label="EPS growth / yr" value={growth} set={setGrowth} min={-20} max={50} suffix="%" />
        <Slider label="Years" value={years} set={setYears} min={1} max={5} />
        <Slider label="Exit P/E" value={exitPe} set={setExitPe} min={5} max={80} suffix="×" />
      </div>

      <div className="flex flex-wrap gap-2 mt-2">
        {[
          ["Implied price", `$${implied.toFixed(2)}`],
          ["vs today", `${totalReturn >= 0 ? "+" : ""}${totalReturn.toFixed(0)}%`, retColor],
          ["CAGR", `${cagr >= 0 ? "+" : ""}${cagr.toFixed(1)}%/yr`, retColor],
          ["Future EPS", `$${futureEps.toFixed(2)}`],
        ].map(([label, val, color]) => (
          <div key={label} className="px-3 py-2 rounded-xl"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
            <div style={{ fontSize: 11, color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>{label}</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: color || "#E2E8F0", fontFamily: "'Fira Code', monospace" }}>{val}</div>
          </div>
        ))}
      </div>
      <p className="text-xs mt-3" style={{ color: "#3D5068", lineHeight: 1.5 }}>
        Simple driver model on TTM EPS (${eps}) — assumes no dilution or buybacks. A sanity check, not a forecast.
      </p>
    </div>
  );
}
