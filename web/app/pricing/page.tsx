"use client";
import { useState } from "react";

const PLANS = [
  { id:"free",  name:"Free",  price:0,    cta:"Start Building My Twin",          badge:null,          features:["10 memories","20 chats/day","Level 1 prediction","No simulation"] },
  { id:"pro",   name:"Pro",   price:1999, cta:"Unlock My Future Decisions",      badge:"Most popular",features:["500 memories","1,000 chats/day","100 simulations/mo","Level 5 prediction"] },
  { id:"ultra", name:"Ultra", price:4999, cta:"Activate Full AI Consciousness",  badge:"Most powerful",features:["Unlimited everything","Full AI Twin","Unlimited simulations","Unlimited prediction depth","Priority support"] },
];

export default function PricingPage() {
  const [loading, setLoading] = useState<string|null>(null);

  const checkout = async (planId: string) => {
    if (planId === "free") { window.location.href = "/signup"; return; }
    setLoading(planId);
    try {
      const r = await fetch("/api/checkout/create-session", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ plan: planId, email:"" }),
      });
      const { checkout_url, error } = await r.json();
      if (error) throw new Error(error);
      window.location.href = checkout_url;
    } catch (e: any) { alert(e.message || "Checkout failed"); }
    finally { setLoading(null); }
  };

  return (
    <div style={{ minHeight:"100vh", background:"#F8F7F2", padding:"60px 20px 80px" }}>
      <div style={{ maxWidth:900, margin:"0 auto" }}>
        <div style={{ textAlign:"center", marginBottom:52 }}>
          <h1 style={{ fontSize:44, fontWeight:800, color:"#1a1a18", letterSpacing:"-0.03em",
            lineHeight:1.1, marginBottom:12 }}>
            Pay for what you use.<br/>Unlock what you need.
          </h1>
          <p style={{ fontSize:16, color:"#888780" }}>
            Start free. Upgrade when your ambitions outgrow your limits.
          </p>
        </div>

        <div style={{ display:"flex", gap:16, alignItems:"stretch" }}>
          {PLANS.map(plan => (
            <div key={plan.id} style={{ flex:1, background:"#fff", borderRadius:16, padding:"28px 24px 24px",
              border: plan.id==="pro" ? "2px solid #1D9E75" : "1.5px solid #E5E2D9",
              display:"flex", flexDirection:"column", position:"relative" }}>
              {plan.badge && (
                <div style={{ position:"absolute", top:-13, left:"50%", transform:"translateX(-50%)",
                  background: plan.id==="pro"?"#1D9E75":"#534AB7", color:"#fff",
                  fontSize:10, fontWeight:700, letterSpacing:"0.06em",
                  padding:"3px 14px", borderRadius:99, whiteSpace:"nowrap" }}>
                  {plan.badge.toUpperCase()}
                </div>
              )}
              <div style={{ fontSize:12, fontWeight:700, letterSpacing:"0.08em",
                color:"#888780", marginBottom:8 }}>{plan.name.toUpperCase()}</div>
              <div style={{ fontSize:38, fontWeight:800, color:"#1a1a18", marginBottom:4,
                letterSpacing:"-0.03em" }}>
                {plan.price === 0 ? "Free" : `$${(plan.price/100).toFixed(2)}`}
                {plan.price > 0 && <span style={{ fontSize:13, fontWeight:400, color:"#888780" }}>/mo</span>}
              </div>
              <button onClick={() => checkout(plan.id)} disabled={loading === plan.id}
                style={{ width:"100%", padding:"11px 0", borderRadius:10, marginBottom:20, marginTop:16,
                  border: plan.id==="pro"?"none":"1.5px solid #2C2C2A",
                  background: plan.id==="pro"?"#1D9E75":"transparent",
                  color: plan.id==="pro"?"#fff":"#1a1a18",
                  fontSize:13, fontWeight:700, cursor:"pointer",
                  opacity: loading===plan.id ? 0.7 : 1 }}>
                {loading===plan.id ? "Loading…" : plan.cta}
              </button>
              <div style={{ flex:1, display:"flex", flexDirection:"column", gap:8 }}>
                {plan.features.map(f => (
                  <div key={f} style={{ display:"flex", alignItems:"center", gap:8 }}>
                    <span style={{ color:"#1D9E75", fontSize:14, fontWeight:700 }}>✓</span>
                    <span style={{ fontSize:13, color:"#2C2C2A" }}>{f}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div style={{ display:"flex", justifyContent:"center", gap:28, marginTop:40, flexWrap:"wrap" }}>
          {["No credit card required","Cancel anytime","256-bit encryption","Instant activation"].map(t => (
            <span key={t} style={{ fontSize:13, color:"#444441" }}>✓ {t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
