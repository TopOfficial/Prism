// Side-by-side bull vs bear arguments extracted from the Deep Research run.

function CaseColumn({ title, icon, color, items }) {
  return (
    <div className="flex-1 min-w-0 rounded-xl p-4"
      style={{ background: `${color}0D`, border: `1px solid ${color}33` }}>
      <div className="flex items-center gap-2 mb-3">
        <span style={{ fontSize: 15 }}>{icon}</span>
        <h5 className="text-xs font-bold uppercase tracking-widest"
          style={{ color, fontFamily: "'Space Grotesk', sans-serif" }}>
          {title}
        </h5>
      </div>
      <ul className="flex flex-col gap-2.5" style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {(items || []).map((item, i) => (
          <li key={i}>
            <p className="text-sm font-semibold" style={{ color: "#E2E8F0", lineHeight: 1.5 }}>{item.point}</p>
            {item.evidence && (
              <p className="text-xs mt-0.5" style={{ color: "#64748B", lineHeight: 1.5 }}>{item.evidence}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function BullBearDebate({ bullBear }) {
  if (!bullBear) return null;
  return (
    <div className="mb-4">
      <h4 className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
        Bull vs Bear
      </h4>
      <div className="flex flex-col md:flex-row gap-3">
        <CaseColumn title="Bull Case" icon="▲" color="#34D399" items={bullBear.bull} />
        <CaseColumn title="Bear Case" icon="▼" color="#F87171" items={bullBear.bear} />
      </div>
      {bullBear.verdict && (
        <div className="mt-3 px-4 py-3 rounded-xl"
          style={{ background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.22)" }}>
          <span className="text-xs font-bold uppercase tracking-widest mr-2"
            style={{ color: "#A855F7", fontFamily: "'Space Grotesk', sans-serif" }}>
            Verdict
          </span>
          <span className="text-sm" style={{ color: "#CBD5E1" }}>{bullBear.verdict}</span>
        </div>
      )}
    </div>
  );
}
