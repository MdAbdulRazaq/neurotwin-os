"use client";
import { useState, useEffect, useRef } from "react";

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
  featureName: string;
  blockedAction: string;
  plan?: string;
}

const LOSS_MESSAGES = [
  "You are losing access to future simulations",
  "Your AI twin is currently limited",
  "Prediction accuracy is reduced without full access",
];

export function PaywallModal({ isOpen, onClose, featureName, blockedAction, plan = "pro" }: PaywallModalProps) {
  const [msgIdx, setMsgIdx] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const t = setInterval(() => setMsgIdx(i => (i + 1) % LOSS_MESSAGES.length), 3500);
    return () => clearInterval(t);
  }, [isOpen]);

  if (!isOpen) return null;

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/checkout/create-session", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ plan, email:"" }),
      });
      const { checkout_url } = await r.json();
      if (checkout_url) window.location.href = checkout_url;
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(26,26,24,0.6)", display:"flex",
      alignItems:"center", justifyContent:"center", zIndex:9999, padding:20 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background:"#fff", borderRadius:18, padding:"36px 32px 28px",
        maxWidth:420, width:"100%", position:"relative" }}>
        <button onClick={onClose} style={{ position:"absolute", top:14, right:16,
          background:"none", border:"none", fontSize:20, cursor:"pointer", color:"#888" }}>×</button>
        <div style={{ fontSize:32, textAlign:"center", marginBottom:12 }}>🔒</div>
        <h2 style={{ fontSize:20, fontWeight:800, textAlign:"center", marginBottom:8,
          color:"#1a1a18", letterSpacing:"-0.02em" }}>{featureName} — Locked</h2>
        <p style={{ fontSize:13, color:"#E24B4A", textAlign:"center", fontWeight:600,
          marginBottom:16, minHeight:20 }}>{LOSS_MESSAGES[msgIdx]}</p>
        <p style={{ fontSize:13, color:"#888780", textAlign:"center", marginBottom:24 }}>
          Unlock <strong>{blockedAction}</strong> by upgrading your plan.
        </p>
        <button onClick={handleUpgrade} disabled={loading} style={{ width:"100%", padding:"13px 0",
          borderRadius:10, border:"none", background:"#1D9E75", color:"#fff",
          fontSize:14, fontWeight:700, cursor:loading?"default":"pointer", opacity:loading?0.7:1 }}>
          {loading ? "Loading..." : "Unlock My Future Now"}
        </button>
        <p style={{ fontSize:11, color:"#B4B2A9", textAlign:"center", marginTop:10 }}>
          Cancel anytime · No lock-in · 256-bit encryption
        </p>
      </div>
    </div>
  );
}
