import { useState } from "react";

const PACKS = [
  { id: "starter",  name: "Starter",  credits: 5,  price: "$3.99",  per: "$0.80/credit" },
  { id: "standard", name: "Standard", credits: 15, price: "$9.99",  per: "$0.67/credit", popular: true },
  { id: "pro",      name: "Pro",      credits: 40, price: "$24.99", per: "$0.62/credit" },
];

export default function PricingModal({ account, onClose, onCheckout }) {
  const [customQty, setCustomQty] = useState(10);

  const qty = Math.max(1, Math.min(Number(customQty) || 1, 999));
  const customTotal = (qty * 0.99).toFixed(2);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: "rgba(3,6,12,0.8)", backdropFilter: "blur(4px)" }}
      onClick={onClose}>
      <div className="relative w-full max-w-2xl rounded-2xl overflow-hidden animate-fade-in-up"
        style={{ background: "#0A0F1E", border: "1px solid rgba(168,85,247,0.3)", boxShadow: "0 20px 80px rgba(0,0,0,0.6)" }}
        onClick={e => e.stopPropagation()}>

        <div className="px-6 py-5" style={{ borderBottom: "1px solid rgba(168,85,247,0.15)" }}>
          <div className="flex items-center justify-between">
            <h2 style={{ fontFamily: "'Cinzel', serif", color: "#A855F7", fontSize: 20, letterSpacing: "0.1em" }}>
              Unlock Deep Research
            </h2>
            <button onClick={onClose}
              style={{ color: "#4E6278", background: "none", border: "none", cursor: "pointer", fontSize: 20, lineHeight: 1 }}>
              ✕
            </button>
          </div>
          <p className="text-sm mt-1" style={{ color: "#64748B" }}>
            1 credit = 1 full 3-phase analysis. Briefs stay free. Everyone gets 1 free Deep Research per week.
            {account?.credits > 0 && <span style={{ color: "#A855F7" }}> You have {account.credits} credits.</span>}
          </p>
        </div>

        <div className="px-6 py-5 flex flex-col gap-5 max-h-[70vh] overflow-y-auto">

          {/* Subscription */}
          <div className="rounded-xl p-4 flex items-center justify-between"
            style={{ background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.35)" }}>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold" style={{ color: "#E2E8F0", fontFamily: "'Space Grotesk', sans-serif" }}>Subscription</span>
                <span className="text-xs px-2 py-0.5 rounded-full font-semibold"
                  style={{ background: "rgba(168,85,247,0.18)", color: "#A855F7", border: "1px solid rgba(168,85,247,0.3)" }}>
                  Unlimited
                </span>
              </div>
              <p className="text-xs mt-1" style={{ color: "#64748B" }}>Unlimited Deep Research. Cancel anytime.</p>
            </div>
            <div className="text-right shrink-0 ml-4">
              <div style={{ color: "#E2E8F0", fontWeight: 700, fontSize: 18 }}>$9.99<span style={{ fontSize: 12, color: "#64748B" }}>/mo</span></div>
              <button onClick={() => onCheckout("subscription")}
                className="mt-1 text-sm font-semibold px-4 py-2 rounded-lg cursor-pointer"
                style={{ background: "#A855F7", border: "none", color: "#fff" }}>
                Subscribe
              </button>
            </div>
          </div>

          {/* Packs */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
              Credit Packs — no subscription
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {PACKS.map(p => (
                <div key={p.id} className="rounded-xl p-4 flex flex-col"
                  style={{ background: "rgba(255,255,255,0.03)", border: `1px solid ${p.popular ? "rgba(168,85,247,0.4)" : "rgba(255,255,255,0.08)"}` }}>
                  {p.popular && (
                    <span className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: "#A855F7" }}>Most popular</span>
                  )}
                  <div style={{ color: "#E2E8F0", fontWeight: 700, fontSize: 15, fontFamily: "'Space Grotesk', sans-serif" }}>{p.name}</div>
                  <div style={{ color: "#A855F7", fontSize: 13, marginTop: 2 }}>{p.credits} credits</div>
                  <div style={{ color: "#E2E8F0", fontWeight: 700, fontSize: 18, marginTop: 8 }}>{p.price}</div>
                  <div style={{ color: "#3D5068", fontSize: 11 }}>{p.per}</div>
                  <button onClick={() => onCheckout(p.id)}
                    className="mt-3 text-sm font-semibold px-3 py-2 rounded-lg cursor-pointer transition-all"
                    style={{ background: "rgba(168,85,247,0.18)", border: "1px solid rgba(168,85,247,0.4)", color: "#A855F7" }}
                    onMouseEnter={e => e.currentTarget.style.background = "rgba(168,85,247,0.28)"}
                    onMouseLeave={e => e.currentTarget.style.background = "rgba(168,85,247,0.18)"}>
                    Buy
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Custom credits */}
          <div className="rounded-xl p-4"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#4E6278", fontFamily: "'Space Grotesk', sans-serif" }}>
              Custom — $0.99 / credit
            </p>
            <div className="flex items-center gap-3">
              <input type="number" min="1" max="999" value={customQty}
                onChange={e => setCustomQty(e.target.value)}
                className="bg-transparent text-white rounded-lg px-3 py-2 w-24 focus:outline-none"
                style={{ border: "1px solid rgba(168,85,247,0.3)", fontFamily: "'Fira Code', monospace" }} />
              <span className="text-sm" style={{ color: "#64748B" }}>credits = <span style={{ color: "#E2E8F0", fontWeight: 600 }}>${customTotal}</span></span>
              <button onClick={() => onCheckout("credits", qty)}
                className="ml-auto text-sm font-semibold px-4 py-2 rounded-lg cursor-pointer"
                style={{ background: "#A855F7", border: "none", color: "#fff" }}>
                Buy {qty} credits
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
