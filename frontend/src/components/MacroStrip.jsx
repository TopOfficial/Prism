import { useState, useEffect } from "react";

// Key macro series (FRED) on the homepage. Renders nothing until the backend
// has a FRED_API_KEY, so it can ship dark and activate later.
export default function MacroStrip({ apiBase }) {
  const [series, setSeries] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase}/macro`);
        if (!res.ok) return;
        const d = await res.json();
        if (!cancelled && d.enabled && d.series?.length) setSeries(d.series);
      } catch { /* strip just doesn't render */ }
    })();
    return () => { cancelled = true; };
  }, [apiBase]);

  if (!series) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-4">
      {series.map(s => (
        <div key={s.id} className="px-3 py-2 rounded-xl"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
          <div style={{ fontSize: 11, color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>{s.label}</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#E2E8F0", fontFamily: "'Fira Code', monospace" }}>
            {s.value}{s.unit}
          </div>
        </div>
      ))}
    </div>
  );
}
