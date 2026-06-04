"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [stage, setStage]       = useState<"form"|"hook">("form");
  const [progress, setProgress] = useState(0);

  const getParam = (key: string) => {
    if (typeof window === "undefined") return "";
    return new URLSearchParams(window.location.search).get(key) || "";
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    try {
      const r = await fetch("/api/auth/signup", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ email, password,
          referral_id: getParam("ref") || getParam("referral"),
          plan_intent: getParam("plan") || "free" }),
      });
      if (!r.ok) { const d = await r.json(); setError(d.detail || "Signup failed"); return; }
      setStage("hook");
      // 4-stage commitment hook
      const steps = [25, 50, 80, 100];
      for (const p of steps) { await new Promise(res => setTimeout(res, 700)); setProgress(p); }
      await new Promise(res => setTimeout(res, 400));
      router.push("/dashboard");
    } catch { setError("Something went wrong. Please try again."); }
  };

  if (stage === "hook") return (
    <div style={{ minHeight:"100vh", display:"flex", flexDirection:"column", alignItems:"center",
      justifyContent:"center", background:"#F8F7F2", padding:20 }}>
      <h2 style={{ fontSize:28, fontWeight:800, color:"#1a1a18", marginBottom:8, textAlign:"center" }}>
        Let's build your AI twin
      </h2>
      <p style={{ fontSize:14, color:"#888780", marginBottom:40 }}>Setting up your intelligence…</p>
      <div style={{ width:300, height:6, background:"#E5E2D9", borderRadius:99, overflow:"hidden" }}>
        <div style={{ height:"100%", width:`${progress}%`, background:"#1D9E75",
          borderRadius:99, transition:"width 0.6s ease" }} />
      </div>
      <p style={{ fontSize:12, color:"#1D9E75", marginTop:12, fontWeight:700 }}>{progress}%</p>
    </div>
  );

  return (
    <div style={{ minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center",
      background:"#F8F7F2", padding:20 }}>
      <div style={{ background:"#fff", border:"1.5px solid #E5E2D9", borderRadius:16,
        padding:"36px 32px", width:"100%", maxWidth:400 }}>
        <h1 style={{ fontSize:24, fontWeight:800, color:"#1a1a18", marginBottom:6 }}>
          Create your account
        </h1>
        <p style={{ fontSize:13, color:"#888780", marginBottom:28 }}>
          Start free. No credit card required.
        </p>
        <form onSubmit={handleSignup}>
          <input type="email" placeholder="Email" value={email} required
            onChange={e => setEmail(e.target.value)}
            style={{ width:"100%", padding:"11px 14px", borderRadius:8,
              border:"1.5px solid #E5E2D9", fontSize:14, marginBottom:12, boxSizing:"border-box" }} />
          <input type="password" placeholder="Password (min 8 chars)" value={password} required
            onChange={e => setPassword(e.target.value)}
            style={{ width:"100%", padding:"11px 14px", borderRadius:8,
              border:"1.5px solid #E5E2D9", fontSize:14, marginBottom:16, boxSizing:"border-box" }} />
          {error && <p style={{ color:"#E24B4A", fontSize:13, marginBottom:12 }}>{error}</p>}
          <button type="submit" style={{ width:"100%", padding:"13px 0",
            background:"#1D9E75", color:"#fff", border:"none", borderRadius:10,
            fontSize:14, fontWeight:700, cursor:"pointer" }}>
            Start Building My Twin
          </button>
        </form>
        <p style={{ fontSize:12, color:"#888780", textAlign:"center", marginTop:16 }}>
          Already have an account? <a href="/login" style={{ color:"#1D9E75" }}>Log in</a>
        </p>
        <p style={{ fontSize:11, color:"#B4B2A9", textAlign:"center", marginTop:8 }}>
          No credit card required · Cancel anytime · 256-bit encryption · Instant activation
        </p>
      </div>
    </div>
  );
}
