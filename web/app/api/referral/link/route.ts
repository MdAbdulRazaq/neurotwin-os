import { NextRequest, NextResponse } from "next/server";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost";
export async function POST(req: NextRequest) {
  const token = req.cookies.get("nt_token")?.value || "";
  const body  = await req.json();
  const r = await fetch(`${API}/api/referral/link`, {
    method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  return NextResponse.json(await r.json(), { status: r.status });
}
