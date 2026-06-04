/**
 * NEUROTWIN OS - Web Health Check Endpoint
 * Returns 200 OK for Docker health checks
 */

export async function GET() {
  const healthStatus = {
    status: "healthy",
    timestamp: new Date().toISOString(),
    service: "neurotwin-web",
    version: "1.0.0",
    uptime: process.uptime(),
  };

  return new Response(JSON.stringify(healthStatus), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache",
    },
  });
}
