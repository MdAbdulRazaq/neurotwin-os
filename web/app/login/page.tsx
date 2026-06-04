"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../hooks/useAuth";

export default function LoginPage() {
  const { login, identify } = useAuth();
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  const getRedirect = () => {
    if (typeof window === "undefined") return "/dashboard";
    return new URLSearchParams(window.location.search).get("redirect") || "/dashboard";
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(email, password);
      identify(email, { email });
      router.push(getRedirect());
    } catch (err: any) {
      setError(err.message || "Login failed. Check your credentials.");
    } finally { setLoading(false); }
  };

  return (
    <div style={{ minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center",
      background:"#F8F7F2", padding:20 }}>
      <div style={{ background:"#fff", border:"1.5px solid #E5E2D9", borderRadius:16,
        padding:"36px 32px", width:"100%", maxWidth:400 }}>
        <h1 style={{ fontSize:24, fontWeight:800, color:"#1a1a18", marginBottom:6 }}>Welcome back</h1>
        <p style={{ fontSize:13, color:"#888780", marginBottom:28 }}>Log in to your AI twin</p>
        <form onSubmit={handleLogin}>
          <input type="email" placeholder="Email" value={email} required
            onChange={e => setEmail(e.target.value)}
            style={{ width:"100%", padding:"11px 14px", borderRadius:8,
              border:"1.5px solid #E5E2D9", fontSize:14, marginBottom:12, boxSizing:"border-box" }} />
          <input type="password" placeholder="Password" value={password} required
            onChange={e => setPassword(e.target.value)}
            style={{ width:"100%", padding:"11px 14px", borderRadius:8,
              border:"1.5px solid #E5E2D9", fontSize:14, marginBottom:16, boxSizing:"border-box" }} />
          {error && <p style={{ color:"#E24B4A", fontSize:13, marginBottom:12 }}>{error}</p>}
          <button type="submit" disabled={loading} style={{ width:"100%", padding:"13px 0",
            background:"#1a1a18", color:"#fff", border:"none", borderRadius:10,
            fontSize:14, fontWeight:700, cursor:loading?"default":"pointer", opacity:loading?0.7:1 }}>
            {loading ? "Logging in…" : "Log in"}
          </button>
        </form>
        <p style={{ fontSize:12, color:"#888780", textAlign:"center", marginTop:16 }}>
          No account? <a href="/signup" style={{ color:"#1D9E75" }}>Sign up free</a>
        </p>
      </div>
    </div>
  );
}
