import { Metadata } from "next";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost";

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  try {
    const r = await fetch(`${API}/api/share/${params.id}`, { next:{ revalidate:3600 } });
    if (r.ok) {
      const d = await r.json();
      return { title: d.simulation_title || "My AI Future",
        description: d.preview_text || "See what AI predicted for my future",
        openGraph: { title: d.simulation_title, description: d.preview_text } };
    }
  } catch {}
  return { title:"NEUROTWIN — AI Future Preview", description:"See what AI predicted" };
}

export default async function SharePage({ params }: { params: { id: string } }) {
  let share: any = null;
  try {
    const r = await fetch(`${API}/api/share/${params.id}`, { next:{ revalidate:3600 } });
    if (r.ok) share = await r.json();
  } catch {}

  if (!share) return (
    <div style={{ minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center",
      background:"#F8F7F2" }}>
      <div style={{ textAlign:"center" }}>
        <h1 style={{ fontSize:24, color:"#1a1a18", marginBottom:8 }}>Link not found</h1>
        <p style={{ color:"#888780" }}>This share link may have expired.</p>
        <a href="/signup" style={{ display:"inline-block", marginTop:16, background:"#1D9E75",
          color:"#fff", borderRadius:8, padding:"10px 24px", textDecoration:"none", fontWeight:700 }}>
          Build My AI Twin — Free
        </a>
      </div>
    </div>
  );

  return (
    <div style={{ minHeight:"100vh", background:"#F8F7F2", padding:"60px 20px" }}>
      <div style={{ maxWidth:560, margin:"0 auto" }}>
        <div style={{ background:"#fff", border:"1.5px solid #E5E2D9", borderRadius:16,
          padding:"32px 28px", marginBottom:24 }}>
          <p style={{ fontSize:12, fontWeight:700, letterSpacing:"0.08em",
            color:"#888780", marginBottom:12 }}>AI SIMULATION PREVIEW</p>
          <h1 style={{ fontSize:22, fontWeight:800, color:"#1a1a18", marginBottom:12 }}>
            {share.simulation_title}
          </h1>
          <p style={{ fontSize:15, color:"#444441", lineHeight:1.6 }}>{share.preview_text}</p>
        </div>
        <div style={{ textAlign:"center" }}>
          <p style={{ fontSize:14, color:"#888780", marginBottom:16 }}>
            This is what my future looks like with AI.
          </p>
          <a href="/signup" style={{ display:"inline-block", background:"#1D9E75",
            color:"#fff", borderRadius:10, padding:"14px 32px",
            textDecoration:"none", fontWeight:800, fontSize:15 }}>
            Build My AI Twin — Free
          </a>
          <p style={{ fontSize:11, color:"#B4B2A9", marginTop:10 }}>
            No credit card required · Instant setup
          </p>
        </div>
      </div>
    </div>
  );
}
