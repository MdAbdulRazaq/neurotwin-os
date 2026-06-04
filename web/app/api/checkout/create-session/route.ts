import { NextRequest, NextResponse } from "next/server";

const STRIPE_KEY = process.env.STRIPE_SECRET_KEY || "";
const PRICES: Record<string,string> = {
  pro:   process.env.STRIPE_PRO_PRICE_ID   || "",
  ultra: process.env.STRIPE_ULTRA_PRICE_ID || "",
};
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost";

export async function POST(req: NextRequest) {
  try {
    const { plan, email } = await req.json();
    const priceId = PRICES[plan];

    if (!STRIPE_KEY) {
      // Dev mock — no Stripe key needed in development
      return NextResponse.json({ checkout_url: `${BASE}/payment/success?mock=1&plan=${plan}` });
    }

    if (!priceId) {
      return NextResponse.json({ error: "Unknown plan or missing Stripe price id" }, { status: 400 });
    }

    const form = new URLSearchParams();
    form.append("mode", "subscription");
    form.append("success_url", `${BASE}/payment/success?session_id={CHECKOUT_SESSION_ID}`);
    form.append("cancel_url", `${BASE}/pricing`);
    form.append("line_items[0][price]", priceId);
    form.append("line_items[0][quantity]", "1");
    form.append("metadata[plan]", plan);

    if (email) {
      form.append("customer_email", email);
    }

    const stripeResponse = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${STRIPE_KEY}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: form.toString(),
    });

    const payload = await stripeResponse.json();
    if (!stripeResponse.ok) {
      throw new Error(payload?.error?.message || "Stripe checkout session creation failed");
    }

    return NextResponse.json({ checkout_url: payload.url });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
