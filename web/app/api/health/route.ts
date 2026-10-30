import { NextResponse } from "next/server";
import { sequelize } from "@/lib/db";
import { logger } from "@/lib/logger";

export async function GET() {
  const startTime = Date.now();
  let dbStatus = "unknown";
  let dbLatencyMs = 0;
  let dbError: string | null = null;

  try {
    const pingStart = Date.now();
    await sequelize.authenticate();
    dbLatencyMs = Date.now() - pingStart;
    dbStatus = "connected";
    logger.info("DB", `Health check: Database is reachable (${dbLatencyMs}ms)`);
  } catch (err: unknown) {
    dbStatus = "disconnected";
    dbError = err instanceof Error ? err.message : String(err);
    logger.error("DB", `Health check: Database unreachable - ${dbError}`);
  }

  const payload = {
    status: dbStatus === "connected" ? "healthy" : "degraded",
    uptimeSeconds: Math.floor(process.uptime()),
    timestamp: new Date().toISOString(),
    services: {
      database: {
        status: dbStatus,
        latencyMs: dbLatencyMs,
        ...(dbError ? { error: dbError } : {}),
      },
      gestureServiceWsUrl: process.env.NEXT_PUBLIC_WS_URL ?? null,
    },
    totalCheckTimeMs: Date.now() - startTime,
  };

  logger.info("APP", `Health check report: ${JSON.stringify(payload)}`);

  return NextResponse.json(payload, {
    status: payload.status === "healthy" ? 200 : 503,
  });
}
