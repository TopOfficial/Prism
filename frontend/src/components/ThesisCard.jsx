import { useState, useEffect } from "react";
import { supabase } from "../lib/supabase";

const VERDICT_COLORS = { stronger: "#34D399", weaker: "#FCD34D", broken: "#F87171", mixed: "#94A3B8" };

// Record why you own this stock; after each earnings the alert job appends a
// stronger/weaker/broken checkpoint that shows up here and in the alert email.
export default function ThesisCard({ ticker, apiBase }) {
  const [thesis, setThesis] = useState(null); // {thesis, checkpoints} | null
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setThesis(null);
    setEditing(false);
    setDraft("");
    (async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || cancelled) return;
        const res = await fetch(`${apiBase}/thesis/${ticker}`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (!res.ok || cancelled) return;
        const d = await res.json();
        setThesis(d);
        setDraft(d.thesis || "");
      } catch { /* no thesis yet */ }
    })();
    return () => { cancelled = true; };
  }, [ticker, apiBase]);

  async function save() {
    const text = draft.trim();
    if (!text || saving) return;
    setSaving(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${apiBase}/thesis/${ticker}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ thesis: text }),
      });
      if (res.ok) {
        setThesis(await res.json());
        setEditing(false);
      }
    } catch { /* leave editor open */ } finally {
      setSaving(false);
    }
  }

  const showEditor = editing || !thesis;

  return (
    <div className="mt-6 pt-5" style={{ borderTop: "1px solid rgba(168,85,247,0.15)" }}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
          Your Thesis
        </h4>
        {thesis && !editing && (
          <button onClick={() => setEditing(true)}
            style={{ fontSize: 12, color: "#3D5068", background: "none", border: "none", cursor: "pointer" }}>
            Edit
          </button>
        )}
      </div>

      {showEditor ? (
        <div>
          <textarea value={draft} onChange={e => setDraft(e.target.value)}
            placeholder={`Why do you own (or want to own) ${ticker}? e.g. "Buying for datacenter growth — expecting margin expansion through 2027."`}
            maxLength={2000} rows={3}
            className="w-full text-sm px-4 py-3 rounded-xl"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#E2E8F0", outline: "none", resize: "vertical" }} />
          <div className="flex items-center gap-3 mt-2">
            <button onClick={save} disabled={saving || !draft.trim()}
              className="text-sm font-semibold px-4 py-2 rounded-xl cursor-pointer"
              style={{ background: saving || !draft.trim() ? "rgba(168,85,247,0.25)" : "#A855F7", border: "none", color: "#fff" }}>
              {saving ? "Saving…" : "Save thesis"}
            </button>
            <span className="text-xs" style={{ color: "#3D5068" }}>
              We&apos;ll check it against every earnings report and tell you if it holds up.
            </span>
          </div>
        </div>
      ) : (
        <div>
          <p className="text-sm px-4 py-3 rounded-xl mb-3"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", color: "#CBD5E1", lineHeight: 1.65 }}>
            {thesis.thesis}
          </p>
          {(thesis.checkpoints || []).length > 0 ? (
            <div className="flex flex-col gap-2">
              {[...thesis.checkpoints].reverse().map((cp, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full shrink-0"
                    style={{ color: VERDICT_COLORS[cp.verdict] || "#94A3B8", border: `1px solid ${VERDICT_COLORS[cp.verdict] || "#94A3B8"}55`, fontFamily: "'Space Grotesk', sans-serif", textTransform: "uppercase" }}>
                    {cp.verdict}
                  </span>
                  <div>
                    <span className="text-xs" style={{ color: "#3D5068" }}>{cp.date}</span>
                    <p className="text-xs" style={{ color: "#94A3B8", lineHeight: 1.6, margin: 0 }}>{cp.note}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs" style={{ color: "#3D5068" }}>
              No checkpoints yet — the first one lands after {ticker}&apos;s next earnings report.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
