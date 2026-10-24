import { NextResponse } from "next/server";
import { getUserId } from "@/lib/session-auth";
import { createSession, listSessionsWithCaptionCount } from "@/lib/repositories/sessions";
import { ERROR_MESSAGES } from "@/lib/constants";
import { logger } from "@/lib/logger";

export async function POST(req: Request) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });
  const session = await createSession(userId);
  logger.info("APP", "Recognition session created", { audit: true, sessionId: String(session.get("id")) });
  return NextResponse.json(session, { status: 201 });
}

export async function GET(req: Request) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });
  return NextResponse.json(await listSessionsWithCaptionCount(userId));
}
