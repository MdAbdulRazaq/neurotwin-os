"use client";
import { useEffect, useState } from "react";

const BENEFITS = [
  { icon:"⚗", title:"Unlimited simulations", desc:"Run as many future scenarios as you need" },
  { icon:"🧠", title:"Full AI twin",          desc:"Complete behavioral model with deep memory" },
  { icon:"🔭", title:"Unlimited prediction",  desc:"No depth limit on future analysis" },
  { icon:"📦", title:"500+ memories",         desc:"Pro, or unlimited on Ultra" },
];

export default function UpgradePage() {
  const [plan, setPlan]     = useState("pro");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("plan");
    if (p === "ultra") setPlan("ultra");
  }, []);

  const handleCheckout = async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/checkout/create-session", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ plan, email:"" }),
      });
      const { checkout_url } = await r.json();
      window.location.href = checkout_url;
    } catch { alert("Checkout failed. Please try again."); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ minHeight:"100vh", background:"#F8F7F2", display:"flex",
      alignItems:"center", justifyContent:"center", padding:20 }}>
      <div style={{ maxWidth:500, width:"100%", textAlign:"center" }}>
        <div style={{ fontSize:40, marginBottom:16 }}>🚀</div>
        <h1 style={{ fontSize:32, fontWeight:800, color:"#1a1a18", marginBottom:8,
          letterSpacing:"-0.02em" }}>
          Full Control Over Your Future
        </h1>
        <p style={{ fontSize:15, color:"#888780", marginBottom:36 }}>
          No limits. Full AI consciousness unlocked. Upgrade now and transform how you make decisions.
        </p>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginBottom:36 }}>
          {BENEFITS.map(b => (
            <div key={b.title} style={{ background:"#fff", border:"1.5px solid #E5E2D9",
              borderRadius:12, padding:"16px 14px", textAlign:"left" }}>
              <div style={{ fontSize:22, marginBottom:6 }}>{b.icon}</div>
              <div style={{ fontSize:13, fontWeight:700, color:"#1a1a18", marginBottom:4 }}>{b.title}</div>
              <div style={{ fontSize:12, color:"#888780" }}>{b.desc}</div>
            </div>
          ))}
        </div>
        <button onClick={handleCheckout} disabled={loading} style={{ width:"100%", padding:"15px 0",
          background:"#1D9E75", color:"#fff", border:"none", borderRadius:12,
          fontSize:15, fontWeight:800, cursor:loading?"default":"pointer",
          opacity:loading?0.7:1, letterSpacing:"0.01em" }}>
          {loading ? "Redirecting to checkout…" : `Upgrade to ${plan.charAt(0).toUpperCase()+plan.slice(1)} now`}
        </button>
        <p style={{ fontSize:11, color:"#B4B2A9", marginTop:12 }}>
          Cancel anytime · No lock-in · Instant activation
        </p>
      </div>
    </div>
  );
}
