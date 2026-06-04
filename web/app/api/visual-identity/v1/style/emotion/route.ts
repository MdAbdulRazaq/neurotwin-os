import { NextRequest, NextResponse } from 'next/server';

/**
 * Proxy route for Visual Identity service.
 * Forwards requests to http://visual-identity:8005/v1/style/emotion
 * This avoids CORS issues in development and production.
 */

const VISUAL_IDENTITY_URL = process.env.VISUAL_IDENTITY_URL || 'http://localhost:8005';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${VISUAL_IDENTITY_URL}/v1/style/emotion`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Visual Identity proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch visual identity' },
      { status: 500 }
    );
  }
}
