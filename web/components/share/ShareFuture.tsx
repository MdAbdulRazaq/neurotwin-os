"use client";
import { useState } from "react";

interface ShareFutureProps { userId: string; simulationTitle: string; previewText: string; }

export function ShareFuture({ userId, simulationTitle, previewText }: ShareFutureProps) {
  const [link, setLink]       = useState("");
  const [copied, setCopied]   = useState(false);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    if (link) { copyLink(link); return; }
    setLoading(true);
    try {
      const r = await fetch("/api/share/create", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ user_id:userId, simulation_title:simulationTitle, preview_text:previewText }),
      });
      if (!r.ok) throw new Error("Share failed");
      const d = await r.json();
      setLink(d.share_url || `${window.location.origin}/share/${d.id}`);
      copyLink(d.share_url);
    } catch (e) { alert("Could not generate share link"); }
    finally { setLoading(false); }
  };

  const copyLink = (url: string) => {
    navigator.clipboard.writeText(url).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2500); });
  };

  const shareOnX = () => {
    const text = encodeURIComponent(`This is what my future looks like with AI — ${link}`);
    window.open(`https://twitter.com/intent/tweet?text=${text}`, "_blank");
  };

  return (
    <div style={{ background:"#F8F7F2", border:"1px solid #E5E2D9", borderRadius:12, padding:"16px 20px" }}>
      <p style={{ fontSize:13, fontWeight:700, color:"#1a1a18", marginBottom:8 }}>
        Share your future
      </p>
      <p style={{ fontSize:12, color:"#888780", marginBottom:14 }}>
        Let others see what AI predicted for you. Every share earns you +5 simulations.
      </p>
      {link && (
        <div style={{ background:"#fff", border:"1px solid #E5E2D9", borderRadius:8,
          padding:"8px 12px", fontSize:12, color:"#444", marginBottom:10,
          wordBreak:"break-all" }}>{link}</div>
      )}
      <div style={{ display:"flex", gap:8 }}>
        <button onClick={generate} disabled={loading} style={{ flex:1, padding:"9px 0",
          background:"#1D9E75", color:"#fff", border:"none", borderRadius:8,
          fontSize:13, fontWeight:700, cursor:"pointer" }}>
          {loading ? "Generating…" : copied ? "Copied!" : link ? "Copy link" : "Generate share link"}
        </button>
        {link && (
          <button onClick={shareOnX} style={{ padding:"9px 14px", background:"#1a1a18",
            color:"#fff", border:"none", borderRadius:8, fontSize:12, cursor:"pointer" }}>
            Share on X
          </button>
        )}
      </div>
    </div>
  );
}
