export default function ErrorState({ ticker, message }) {
  return (
    <div
      className="animate-fade-in-up rounded-2xl p-5 mt-2"
      style={{
        background: "rgba(248,113,113,0.05)",
        border: "1px solid rgba(248,113,113,0.3)",
        boxShadow: "0 0 28px rgba(248,113,113,0.08)",
      }}
    >
      <div className="flex items-start gap-4">
        <div
          className="shrink-0 flex items-center justify-center rounded-full"
          style={{ width: 40, height: 40, background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.3)" }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F87171" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-white mb-1" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            Could not load{" "}
            <span style={{ color: "#F87171", fontFamily: "'Fira Code', monospace" }}>{ticker}</span>
          </p>
          {message && <p className="text-sm" style={{ color: "#94A3B8" }}>{message}</p>}
          <p className="text-xs mt-2" style={{ color: "#3D5068" }}>
            Check the ticker symbol or try again later.
          </p>
        </div>
      </div>
    </div>
  );
}
