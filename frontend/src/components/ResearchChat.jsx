import { useState, useEffect, useRef } from "react";
import { supabase } from "../lib/supabase";

// Follow-up chat under a Deep Research report. Thread is per (user, ticker)
// and persists server-side; free users get 5 questions per ticker.
export default function ResearchChat({ ticker, apiBase, onUpgrade }) {
  const [messages, setMessages] = useState([]);
  const [turnsUsed, setTurnsUsed] = useState(0);
  const [turnLimit, setTurnLimit] = useState(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [limitHit, setLimitHit] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setMessages([]);
    setTurnsUsed(0);
    setLimitHit(false);
    (async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || cancelled) return;
        const res = await fetch(`${apiBase}/chat/${ticker}`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (!res.ok || cancelled) return;
        const d = await res.json();
        setMessages(d.messages || []);
        setTurnsUsed(d.turns_used || 0);
        setTurnLimit(d.turn_limit ?? null);
      } catch { /* chat just starts empty */ }
    })();
    return () => { cancelled = true; };
  }, [ticker, apiBase]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, sending]);

  async function send() {
    const message = input.trim();
    if (!message || sending) return;
    setSending(true);
    setInput("");
    setMessages(m => [...m, { role: "user", content: message }]);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${apiBase}/chat/${ticker}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ message }),
      });
      if (res.status === 402) { setLimitHit(true); return; }
      if (!res.ok) throw new Error();
      const d = await res.json();
      setMessages(m => [...m, { role: "assistant", content: d.reply }]);
      setTurnsUsed(d.turns_used);
      setTurnLimit(d.turn_limit ?? null);
    } catch {
      setMessages(m => [...m, { role: "assistant", content: "Something went wrong — try that again." }]);
    } finally {
      setSending(false);
    }
  }

  const turnsLeft = turnLimit != null ? Math.max(turnLimit - turnsUsed, 0) : null;
  const outOfTurns = limitHit || (turnLimit != null && turnsUsed >= turnLimit);

  return (
    <div className="mt-6 pt-5" style={{ borderTop: "1px solid rgba(168,85,247,0.15)" }}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
          Ask about this report
        </h4>
        {turnsLeft != null && !outOfTurns && (
          <span style={{ fontSize: 11, color: "#3D5068", fontFamily: "'Space Grotesk', sans-serif" }}>
            {turnsLeft} question{turnsLeft === 1 ? "" : "s"} left on {ticker}
          </span>
        )}
      </div>

      {messages.length > 0 && (
        <div className="flex flex-col gap-3 mb-3" style={{ maxHeight: 420, overflowY: "auto" }}>
          {messages.map((m, i) => (
            <div key={i} className="px-4 py-3 rounded-xl"
              style={m.role === "user"
                ? { background: "rgba(168,85,247,0.1)", border: "1px solid rgba(168,85,247,0.25)", alignSelf: "flex-end", maxWidth: "85%" }
                : { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", alignSelf: "flex-start", maxWidth: "85%" }}>
              <p className="text-sm" style={{ color: m.role === "user" ? "#CBD5E1" : "#94A3B8", lineHeight: 1.65, whiteSpace: "pre-wrap", margin: 0 }}>
                {m.content}
              </p>
            </div>
          ))}
          {sending && (
            <p className="text-xs" style={{ color: "#4E6278" }}>Thinking…</p>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {outOfTurns ? (
        <div className="px-4 py-3 rounded-xl flex items-center justify-between flex-wrap gap-2"
          style={{ background: "rgba(168,85,247,0.07)", border: "1px solid rgba(168,85,247,0.22)" }}>
          <span className="text-xs" style={{ color: "#94A3B8" }}>
            You&apos;ve used your {turnLimit} free questions on {ticker}. Subscribe for unlimited research chat.
          </span>
          <button onClick={onUpgrade}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg cursor-pointer"
            style={{ background: "#A855F7", border: "none", color: "#fff" }}>
            Upgrade
          </button>
        </div>
      ) : (
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={`Ask anything about ${ticker} — "why is the moat score a 9?"`}
            maxLength={1000}
            className="flex-1 text-sm px-4 py-2.5 rounded-xl"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "#E2E8F0", outline: "none" }}
          />
          <button onClick={send} disabled={sending || !input.trim()}
            className="text-sm font-semibold px-4 py-2.5 rounded-xl cursor-pointer shrink-0"
            style={{ background: sending || !input.trim() ? "rgba(168,85,247,0.25)" : "#A855F7", border: "none", color: "#fff" }}>
            Send
          </button>
        </div>
      )}
    </div>
  );
}
