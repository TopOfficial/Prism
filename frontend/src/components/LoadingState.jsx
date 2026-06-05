function Skel({ h = 16, w = "100%", radius = 8 }) {
  return <div className="skeleton" style={{ height: h, width: w, borderRadius: radius }} />;
}

function Card({ children }) {
  return (
    <div style={{
      background: "rgba(10,15,30,0.85)",
      border: "1px solid rgba(56,189,248,0.12)",
      borderRadius: 16,
      padding: "20px",
    }}>
      {children}
    </div>
  );
}

export default function LoadingState({ ticker }) {
  return (
    <div className="animate-fade-in space-y-4">

      {/* Header skeleton */}
      <Card>
        <div className="flex justify-between items-start gap-4">
          <div className="space-y-2 flex-1">
            <Skel h={22} w="55%" />
            <div className="flex gap-2">
              <Skel h={18} w={60} />
              <Skel h={18} w={80} />
            </div>
          </div>
          <div className="space-y-2 text-right">
            <Skel h={28} w={100} />
            <Skel h={16} w={70} />
          </div>
        </div>
        <Skel h={4} radius={9} style={{ marginTop: 16 }} />
        <div className="flex justify-between mt-2">
          <Skel h={12} w={50} />
          <Skel h={12} w={50} />
        </div>
      </Card>

      {/* Scores skeleton */}
      <Card>
        <Skel h={12} w={100} radius={4} />
        <div className="mt-4 flex gap-4 items-start">
          <Skel h={72} w={72} radius={9999} />
          <div className="flex-1 space-y-4 pt-2">
            {[80, 65, 90, 55].map((w, i) => (
              <div key={i}>
                <div className="flex justify-between mb-1.5">
                  <Skel h={11} w={`${w}%`} />
                  <Skel h={11} w={28} />
                </div>
                <Skel h={6} radius={9} />
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Grid skeleton */}
      <Card>
        <Skel h={12} w={80} radius={4} />
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mt-4">
          {Array(6).fill(0).map((_, i) => (
            <div key={i} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: 12, padding: 14 }}>
              <Skel h={11} w="60%" />
              <Skel h={18} w="75%" radius={4} />
            </div>
          ))}
        </div>
      </Card>

      {/* Table skeleton */}
      <Card>
        <Skel h={12} w={110} radius={4} />
        <div className="mt-4 space-y-3">
          {Array(4).fill(0).map((_, i) => (
            <div key={i} className="flex gap-4">
              <Skel h={13} w="25%" />
              <Skel h={13} w="20%" />
              <Skel h={13} w="20%" />
              <Skel h={13} w="25%" />
            </div>
          ))}
        </div>
      </Card>

      {/* Spinner label */}
      <div className="flex items-center justify-center gap-3 py-4">
        <div className="neon-spinner" />
        <p className="text-sm" style={{ color: "#38BDF8", fontFamily: "'Fira Code', monospace" }}>
          Analyzing <strong>{ticker}</strong>
        </p>
      </div>
    </div>
  );
}
