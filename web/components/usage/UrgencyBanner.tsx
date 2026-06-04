"use client";
import { useState, useEffect, useRef } from "react";

interface UsageData { plan:string; warning:boolean; simulations:{ used:number; limit:number; pct:number }; }
const POLL_MS = 120_000; // 2 min

export function UrgencyBanner() {
  const [data, setData] = useState<UsageData|null>(null);
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<NodeJS.Timeout>();

  const fetchUsage = async () => {
    try {
      const r = await fetch("/api/usage/status");
      if (r.ok) { const d = await r.json(); setData(d); setVisible(d.warning || d.simulations?.pct >= 80); }
    } catch {}
  };

  useEffect(() => {
    fetchUsage();
    timerRef.current = setInterval(fetchUsage, POLL_MS);
    return () => clearInterval(timerRef.current);
  }, []);

  if (!visible || !data) return null;

  const { pct, used, limit } = data.simulations;
  const isExhausted = used >= limit && limit !== -1;
  const msg = isExhausted
    ? "Only 1 simulation left — upgrade before you lose access"
    : `■■ You've used ${pct}% of your AI capacity`;

  return (
    <div style={{ background: isExhausted ? "#FCEBEB" : "#FAEEDA",
      borderBottom: `1px solid ${isExhausted ? "#F09595" : "#EF9F27"}`,
      padding:"10px 20px", display:"flex", alignItems:"center", justifyContent:"space-between",
      fontSize:13, color: isExhausted ? "#A32D2D" : "#854F0B" }}>
      <span>{msg}</span>
      <div style={{ display:"flex", gap:12, alignItems:"center" }}>
        <div style={{ width:120, height:4, background: isExhausted?"#F7C1C1":"#FAC775", borderRadius:99 }}>
          <div style={{ width:`${pct}%`, height:"100%", background: isExhausted?"#E24B4A":"#BA7517",
            borderRadius:99, transition:"width 0.4s" }} />
        </div>
        <a href="/pricing" style={{ fontWeight:700, color:"inherit", textDecoration:"underline" }}>
          Upgrade now
        </a>
      </div>
    </div>
  );
}
