import { useState } from "react";
import { supabase } from "../lib/supabase";

const INPUT = {
  width: "100%",
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(168,85,247,0.2)",
  borderRadius: 10,
  padding: "10px 14px",
  color: "#E2E8F0",
  fontSize: 14,
  fontFamily: "'Space Grotesk', sans-serif",
  outline: "none",
};

const BTN_PRIMARY = {
  width: "100%",
  padding: "11px 0",
  borderRadius: 10,
  background: "#A855F7",
  border: "none",
  color: "#fff",
  fontSize: 14,
  fontWeight: 600,
  fontFamily: "'Space Grotesk', sans-serif",
  cursor: "pointer",
  transition: "opacity 0.15s",
};

const BTN_GOOGLE = {
  width: "100%",
  padding: "10px 0",
  borderRadius: 10,
  background: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.12)",
  color: "#CBD5E1",
  fontSize: 14,
  fontFamily: "'Space Grotesk', sans-serif",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 8,
  transition: "background 0.15s",
};

export default function AuthModal({ onClose }) {
  const [tab, setTab] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (tab === "signin") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        onClose();
      } else {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setSuccess("Check your email to confirm your account.");
      }
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle() {
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({ provider: "google" });
    if (error) setError(error.message);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: "rgba(7,11,20,0.85)", backdropFilter: "blur(6px)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-sm rounded-2xl p-6"
        style={{ background: "#0D1422", border: "1px solid rgba(168,85,247,0.25)", boxShadow: "0 0 60px rgba(168,85,247,0.12)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 style={{ fontFamily: "'Cinzel', serif", color: "#A855F7", fontSize: 18, letterSpacing: "0.12em" }}>
            {tab === "signin" ? "Sign In" : "Create Account"}
          </h2>
          <button onClick={onClose} style={{ color: "#4E6278", background: "none", border: "none", cursor: "pointer", fontSize: 20, lineHeight: 1 }}>
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="flex mb-5 rounded-lg overflow-hidden" style={{ border: "1px solid rgba(168,85,247,0.18)" }}>
          {["signin", "signup"].map((t) => (
            <button key={t} onClick={() => { setTab(t); setError(null); setSuccess(null); }}
              style={{
                flex: 1, padding: "8px 0", fontSize: 13, fontFamily: "'Space Grotesk', sans-serif",
                background: tab === t ? "rgba(168,85,247,0.18)" : "transparent",
                color: tab === t ? "#A855F7" : "#4E6278",
                border: "none", cursor: "pointer", transition: "all 0.15s",
              }}>
              {t === "signin" ? "Sign In" : "Sign Up"}
            </button>
          ))}
        </div>

        {success ? (
          <p style={{ color: "#34D399", fontSize: 14, textAlign: "center", lineHeight: 1.6 }}>{success}</p>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <input
              type="email" placeholder="Email" required
              value={email} onChange={(e) => setEmail(e.target.value)}
              style={INPUT}
            />
            <input
              type="password" placeholder="Password" required
              value={password} onChange={(e) => setPassword(e.target.value)}
              style={INPUT}
            />
            {error && <p style={{ color: "#F87171", fontSize: 13, margin: 0 }}>{error}</p>}
            <button type="submit" disabled={loading} style={{ ...BTN_PRIMARY, opacity: loading ? 0.6 : 1 }}>
              {loading ? "..." : tab === "signin" ? "Sign In" : "Create Account"}
            </button>
          </form>
        )}

        <div className="flex items-center gap-3 my-4">
          <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
          <span style={{ color: "#3D5068", fontSize: 12 }}>or</span>
          <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
        </div>

        <button onClick={handleGoogle} style={BTN_GOOGLE}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.09)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}>
          <svg width="16" height="16" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>
      </div>
    </div>
  );
}
