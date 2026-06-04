import { NextRequest, NextResponse } from "next/server";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost";
const FALLBACK = { plan: "free", simulations: { used: 0, limit: 5, pct: 0 }, warning: false };

export async function GET(req: NextRequest) {
  try {
    const token = req.cookies.get("nt_token")?.value;
    const headers: Record<string,string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const upstream = await fetch(`${API}/api/usage/status`, { headers });
    if (!upstream.ok) return NextResponse.json(FALLBACK);
    return NextResponse.json(await upstream.json());
  } catch {
    return NextResponse.json(FALLBACK); // safe fallback — UrgencyBanner never crashes
  }
}
