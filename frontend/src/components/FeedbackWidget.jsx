import { useState } from "react";

export default function FeedbackWidget({ ticker, verdict, apiBase }) {
  const [vote, setVote] = useState(null);       // "up" | "down"
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);

  async function submit(thumbs) {
    if (submitted || sending) return;
    setVote(thumbs);
    setSending(true);
    try {
      await fetch(`${apiBase}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, verdict, thumbs, comment }),
      });
    } catch (_) {
      // best-effort — don't block UI on network failure
    } finally {
      setSending(false);
      if (!comment) setSubmitted(true);
    }
  }

  async function submitWithComment() {
    if (submitted || sending) return;
    setSending(true);
    try {
      await fetch(`${apiBase}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, verdict, thumbs: vote, comment }),
      });
    } catch (_) {}
    finally {
      setSending(false);
      setSubmitted(true);
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-2 py-3 px-4 rounded-xl animate-fade-in"
        style={{ background: "rgba(168,85,247,0.06)", border: "1px solid rgba(168,85,247,0.15)" }}>
        <span style={{ color: "#A855F7", fontSize: 14 }}>✓</span>
        <span className="text-xs" style={{ color: "#64748B" }}>Thanks for the feedback.</span>
      </div>
    );
  }

  return (
    <div className="animate-fade-in-up rounded-xl p-4"
      style={{ background: "rgba(168,85,247,0.04)", border: "1px solid rgba(168,85,247,0.12)", animationDelay: "0.3s" }}>
      <p className="text-xs mb-3" style={{ color: "#475569", fontFamily: "'Space Grotesk', sans-serif" }}>
        Was this analysis helpful?
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => submit("up")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all duration-150"
          style={{
            background: vote === "up" ? "rgba(52,211,153,0.15)" : "rgba(255,255,255,0.04)",
            border: vote === "up" ? "1px solid rgba(52,211,153,0.4)" : "1px solid rgba(255,255,255,0.08)",
            color: vote === "up" ? "#34D399" : "#475569",
          }}
        >
          👍 Yes
        </button>
        <button
          onClick={() => submit("down")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all duration-150"
          style={{
            background: vote === "down" ? "rgba(248,113,113,0.15)" : "rgba(255,255,255,0.04)",
            border: vote === "down" ? "1px solid rgba(248,113,113,0.4)" : "1px solid rgba(255,255,255,0.08)",
            color: vote === "down" ? "#F87171" : "#475569",
          }}
        >
          👎 No
        </button>
      </div>

      {/* Optional comment — only shown after voting */}
      {vote && (
        <div className="mt-3 animate-fade-in-up">
          <input
            type="text"
            value={comment}
            onChange={e => setComment(e.target.value)}
            onKeyDown={e => e.key === "Enter" && comment.trim() && submitWithComment()}
            placeholder="Anything specific? (optional)"
            maxLength={200}
            className="w-full bg-transparent text-xs py-2 px-3 rounded-lg focus:outline-none"
            style={{
              border: "1px solid rgba(168,85,247,0.2)",
              color: "#94A3B8",
              fontFamily: "'Inter', sans-serif",
            }}
          />
          {comment.trim() && (
            <button
              onClick={submitWithComment}
              disabled={sending}
              className="mt-2 text-xs px-3 py-1.5 rounded-lg cursor-pointer transition-all duration-150 disabled:opacity-40"
              style={{
                background: "rgba(168,85,247,0.12)",
                border: "1px solid rgba(168,85,247,0.3)",
                color: "#A855F7",
              }}
            >
              {sending ? "Sending…" : "Send"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
