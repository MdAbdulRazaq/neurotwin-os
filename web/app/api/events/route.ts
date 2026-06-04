import { NextRequest, NextResponse } from "next/server";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost";

export async function POST(req: NextRequest) {
  // Non-blocking fire-and-forget. Always returns 202 — never blocks the user for analytics.
  try {
    const body = await req.json();
    fetch(`${API}/api/events`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), keepalive: true,
    }).catch(() => {});
  } catch (_) {}
  return NextResponse.json({ accepted: true }, { status: 202 });
}
