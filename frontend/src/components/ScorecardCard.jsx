// Investment scorecard: six 1-10 axes + overall grade, with a canvas-drawn
// PNG download (1200x630, OG-sized) so users can share it — no image libs needed.

const AXES = [
  { key: "growth", label: "Growth" },
  { key: "profitability", label: "Profitability" },
  { key: "moat", label: "Moat" },
  { key: "management", label: "Management" },
  { key: "valuation", label: "Valuation" },
  { key: "risk", label: "Risk" },
];

function scoreColor(score) {
  if (score >= 8) return "#34D399";
  if (score >= 6) return "#A855F7";
  if (score >= 4) return "#FCD34D";
  return "#F87171";
}

function gradeColor(grade) {
  const g = (grade || "")[0];
  if (g === "A") return "#34D399";
  if (g === "B") return "#A855F7";
  if (g === "C") return "#FCD34D";
  return "#F87171";
}

// Draws the shareable card on an offscreen canvas and triggers a PNG download.
function downloadPng(ticker, companyName, scorecard) {
  const W = 1200, H = 630;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#070B14";
  ctx.fillRect(0, 0, W, H);

  // Subtle grid, matching the app background
  ctx.strokeStyle = "rgba(168,85,247,0.05)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= W; x += 64) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  for (let y = 0; y <= H; y += 64) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

  // Header
  ctx.fillStyle = "#A855F7";
  ctx.font = "600 30px Georgia, serif";
  ctx.fillText("P R I S M", 60, 78);
  ctx.fillStyle = "#E2E8F0";
  ctx.font = "700 52px -apple-system, 'Segoe UI', sans-serif";
  ctx.fillText(ticker, 60, 150);
  if (companyName) {
    ctx.fillStyle = "#64748B";
    ctx.font = "400 26px -apple-system, 'Segoe UI', sans-serif";
    ctx.fillText(companyName.slice(0, 42), 60, 188);
  }

  // Overall grade circle (top right)
  const grade = scorecard.overall_grade || "—";
  const gc = gradeColor(grade);
  ctx.beginPath();
  ctx.arc(1050, 120, 68, 0, Math.PI * 2);
  ctx.strokeStyle = gc;
  ctx.lineWidth = 5;
  ctx.stroke();
  ctx.fillStyle = gc;
  ctx.font = "700 56px -apple-system, 'Segoe UI', sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(grade, 1050, 140);
  ctx.font = "600 16px -apple-system, 'Segoe UI', sans-serif";
  ctx.fillStyle = "#64748B";
  ctx.fillText("OVERALL", 1050, 215);
  ctx.textAlign = "left";

  // Score bars
  const top = 265, rowH = 52, labelX = 60, barX = 260, barW = 700, barH = 14;
  AXES.forEach(({ key, label }, i) => {
    const s = scorecard[key]?.score ?? 0;
    const y = top + i * rowH;
    ctx.fillStyle = "#94A3B8";
    ctx.font = "600 22px -apple-system, 'Segoe UI', sans-serif";
    ctx.fillText(label, labelX, y + barH);
    ctx.fillStyle = "rgba(255,255,255,0.07)";
    ctx.beginPath();
    ctx.roundRect(barX, y, barW, barH, 7);
    ctx.fill();
    ctx.fillStyle = scoreColor(s);
    ctx.beginPath();
    ctx.roundRect(barX, y, Math.max(barW * (s / 10), barH), barH, 7);
    ctx.fill();
    ctx.font = "700 24px -apple-system, 'Segoe UI', sans-serif";
    ctx.fillText(String(s), barX + barW + 28, y + barH + 2);
  });

  // Footer
  ctx.fillStyle = "#3D5068";
  ctx.font = "400 20px -apple-system, 'Segoe UI', sans-serif";
  ctx.fillText("AI investment scorecard · not financial advice", 60, 592);
  ctx.fillStyle = "#A855F7";
  ctx.font = "600 22px -apple-system, 'Segoe UI', sans-serif";
  ctx.textAlign = "right";
  ctx.fillText("prisminv.com", 1140, 592);
  ctx.textAlign = "left";

  const a = document.createElement("a");
  a.download = `prism-scorecard-${ticker}.png`;
  a.href = canvas.toDataURL("image/png");
  a.click();
}

export default function ScorecardCard({ ticker, companyName, scorecard }) {
  if (!scorecard) return null;
  const grade = scorecard.overall_grade || "—";

  return (
    <div className="rounded-2xl p-5 mb-4"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(168,85,247,0.2)" }}>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h4 className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
            Investment Scorecard
          </h4>
          <span className="text-sm font-bold px-2.5 py-0.5 rounded-full"
            style={{ color: gradeColor(grade), border: `1.5px solid ${gradeColor(grade)}`, fontFamily: "'Space Grotesk', sans-serif" }}>
            {grade}
          </span>
        </div>
        <button onClick={() => downloadPng(ticker, companyName, scorecard)}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg cursor-pointer transition-all"
          style={{ background: "rgba(168,85,247,0.12)", border: "1px solid rgba(168,85,247,0.3)", color: "#A855F7" }}
          onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.22)"}
          onMouseLeave={e => e.currentTarget.style.background = "rgba(168,85,247,0.12)"}>
          ↓ Download card
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3">
        {AXES.map(({ key, label }) => {
          const axis = scorecard[key] || {};
          const s = axis.score ?? 0;
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold" style={{ color: "#94A3B8", fontFamily: "'Space Grotesk', sans-serif" }}>{label}</span>
                <span className="text-xs font-bold" style={{ color: scoreColor(s), fontFamily: "'Fira Code', monospace" }}>{s}/10</span>
              </div>
              <div className="rounded-full overflow-hidden" style={{ height: 6, background: "rgba(255,255,255,0.07)" }}>
                <div className="h-full rounded-full transition-all"
                  style={{ width: `${s * 10}%`, background: scoreColor(s) }} />
              </div>
              {axis.reason && (
                <p className="text-xs mt-1" style={{ color: "#4E6278", lineHeight: 1.5 }}>{axis.reason}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
