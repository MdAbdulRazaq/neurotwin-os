"use client";
import { useState, useEffect, useRef, ReactNode } from "react";

interface PreviewHookProps {
  children: ReactNode;
  previewPct?: number;
  hookMessage?: string;
  onPaywall: () => void;
}

export function PreviewHook({ children, previewPct = 20, hookMessage = "Here's a glimpse of your future…", onPaywall }: PreviewHookProps) {
  const [revealed, setRevealed] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !revealed) {
        setRevealed(true);
        setTimeout(() => onPaywall(), 1200);
      }
    }, { threshold: 0.6 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [revealed, onPaywall]);

  return (
    <div style={{ position:"relative" }}>
      <div style={{ maxHeight:`${previewPct}vh`, overflow:"hidden", position:"relative" }}>
        {children}
        <div style={{ position:"absolute", bottom:0, left:0, right:0, height:80,
          background:"linear-gradient(transparent, rgba(248,247,242,0.96))" }} />
      </div>
      <div ref={ref} style={{ padding:"20px 0", textAlign:"center" }}>
        <p style={{ fontSize:13, color:"#888780", fontStyle:"italic", marginBottom:12 }}>
          {hookMessage}
        </p>
        <button onClick={onPaywall} style={{ background:"#1D9E75", color:"#fff",
          border:"none", borderRadius:8, padding:"10px 24px",
          fontSize:13, fontWeight:700, cursor:"pointer" }}>
          Unlock Full Access
        </button>
      </div>
    </div>
  );
}
