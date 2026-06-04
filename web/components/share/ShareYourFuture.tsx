"use client";
import { useState } from "react";

interface ShareYourFutureProps { userId: string; }

export function ShareYourFuture({ userId }: ShareYourFutureProps) {
  const [link, setLink]     = useState("");
  const [copied, setCopied] = useState(false);

  const getLink = async () => {
    if (link) { copy(link); return; }
    try {
      const r = await fetch("/api/referral/link", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ user_id: userId }),
      });
      const d = await r.json();
      setLink(d.link); copy(d.link);
    } catch { alert("Could not load referral link"); }
  };

  const copy = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopied(true); setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div style={{ border:"1px dashed #1D9E75", borderRadius:12, padding:"16px 20px", background:"#F6FBF8" }}>
      <p style={{ fontSize:13, fontWeight:700, color:"#085041", marginBottom:6 }}>
        Invite friends — earn simulations
      </p>
      <p style={{ fontSize:12, color:"#0F6E56", marginBottom:12 }}>
        Share your link. Each friend who signs up gives you +5 simulations and them +10 free.
      </p>
      <button onClick={getLink} style={{ width:"100%", padding:"10px 0",
        background:"#1D9E75", color:"#fff", border:"none", borderRadius:8,
        fontSize:13, fontWeight:700, cursor:"pointer" }}>
        {copied ? "Copied!" : link ? "Copy my link" : "Get my referral link"}
      </button>
      {link && (
        <p style={{ fontSize:11, color:"#0F6E56", marginTop:8, wordBreak:"break-all" }}>{link}</p>
      )}
    </div>
  );
}
