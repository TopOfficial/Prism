import { useState } from "react";

export default function ProfileModal({ user, account, onClose, onSignOut, onDeleteAccount, onManageSubscription }) {
  const [confirming, setConfirming] = useState(null); // null | "signout" | "delete"
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);

  const name =
    user?.user_metadata?.full_name ||
    user?.user_metadata?.name ||
    user?.email?.split("@")[0] ||
    "—";

  const creditsLabel =
    account?.is_admin ? "Unlimited (Admin)"
    : account?.is_subscriber ? "Unlimited (Pro)"
    : `${account?.credits ?? 0} credit${account?.credits === 1 ? "" : "s"}`;

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    const ok = await onDeleteAccount();
    if (!ok) {
      setError("Couldn't delete your account. Please try again or contact support.");
      setDeleting(false);
    }
    // On success the parent signs out + closes; nothing more to do here.
  }

  const Row = ({ label, value }) => (
    <div className="flex items-center justify-between py-2.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
      <span className="text-xs uppercase tracking-wider" style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>{label}</span>
      <span className="text-sm" style={{ color: "#CBD5E1" }}>{value}</span>
    </div>
  );

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center px-4"
      style={{ background: "rgba(7,11,20,0.85)", backdropFilter: "blur(6px)" }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="w-full max-w-sm rounded-2xl p-6 animate-fade-in-up"
        style={{ background: "#0D1422", border: "1px solid rgba(168,85,247,0.25)", boxShadow: "0 0 60px rgba(168,85,247,0.12)" }}>

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h2 style={{ fontFamily: "'Cinzel', serif", color: "#A855F7", fontSize: 18, letterSpacing: "0.12em" }}>
            Account
          </h2>
          <button onClick={onClose} style={{ color: "#4E6278", background: "none", border: "none", cursor: "pointer", fontSize: 20, lineHeight: 1 }}>×</button>
        </div>

        {/* Info */}
        <div className="mb-4">
          <Row label="Name" value={name} />
          <Row label="Email" value={user?.email || "—"} />
          <Row label="Credits" value={creditsLabel} />
        </div>

        {/* Manage subscription — only for subscribers */}
        {account?.is_subscriber && (
          <button onClick={onManageSubscription}
            className="text-xs font-medium mb-5 cursor-pointer transition-opacity"
            style={{ color: "#A855F7", background: "none", border: "none", padding: 0, opacity: 0.9 }}
            onMouseEnter={e => e.currentTarget.style.opacity = 1}
            onMouseLeave={e => e.currentTarget.style.opacity = 0.9}>
            Manage subscription &amp; billing →
          </button>
        )}

        {error && <p className="text-xs mb-3" style={{ color: "#F87171" }}>{error}</p>}

        {/* Default: the two action buttons side by side */}
        {!confirming && (
          <div className="flex gap-3">
            <button onClick={() => setConfirming("signout")}
              className="flex-1 text-sm font-medium px-3 py-2.5 rounded-lg cursor-pointer transition-all"
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#CBD5E1" }}>
              Sign Out
            </button>
            <button onClick={() => setConfirming("delete")}
              className="flex-1 text-sm font-medium px-3 py-2.5 rounded-lg cursor-pointer transition-all"
              style={{ background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.35)", color: "#F87171" }}>
              Delete Account
            </button>
          </div>
        )}

        {/* Confirm: Sign Out */}
        {confirming === "signout" && (
          <div className="animate-fade-in">
            <p className="text-sm mb-3" style={{ color: "#CBD5E1" }}>Sign out of your account?</p>
            <div className="flex gap-3">
              <button onClick={() => setConfirming(null)}
                className="flex-1 text-sm px-3 py-2.5 rounded-lg cursor-pointer"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#64748B" }}>
                Cancel
              </button>
              <button onClick={onSignOut}
                className="flex-1 text-sm font-semibold px-3 py-2.5 rounded-lg cursor-pointer"
                style={{ background: "#A855F7", border: "none", color: "#fff" }}>
                Sign Out
              </button>
            </div>
          </div>
        )}

        {/* Confirm: Delete Account */}
        {confirming === "delete" && (
          <div className="animate-fade-in">
            <p className="text-sm mb-1" style={{ color: "#F87171", fontWeight: 600 }}>Delete your account?</p>
            <div className="mb-3 px-3 py-2.5 rounded-lg"
              style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.25)" }}>
              <p className="text-xs" style={{ color: "#FECACA", lineHeight: 1.6 }}>
                ⚠️ Account deletion is <strong>permanent and immediate</strong>. It wipes your account,
                research history, and remaining credits, and cancels any active subscription. It does
                <strong> not auto-refund</strong> unused credits or partial subscription time. This cannot be undone.
              </p>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setConfirming(null)} disabled={deleting}
                className="flex-1 text-sm px-3 py-2.5 rounded-lg cursor-pointer disabled:opacity-40"
                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#64748B" }}>
                Cancel
              </button>
              <button onClick={handleDelete} disabled={deleting}
                className="flex-1 text-sm font-semibold px-3 py-2.5 rounded-lg cursor-pointer disabled:opacity-50"
                style={{ background: "#F87171", border: "none", color: "#fff" }}>
                {deleting ? "Deleting…" : "Delete Forever"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
