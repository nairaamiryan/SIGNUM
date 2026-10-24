import { NextResponse } from "next/server";
import { getUserId } from "@/lib/session-auth";
import { endUserSession } from "@/lib/repositories/sessions";
import { ERROR_MESSAGES } from "@/lib/constants";
import { logger } from "@/lib/logger";

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });

  const { id } = await params;
  if (!(await endUserSession(id, userId))) {
    return NextResponse.json({ error: ERROR_MESSAGES.NOT_FOUND }, { status: 404 });
  }
  logger.info("APP", "Recognition session ended", { audit: true, sessionId: id });
  return NextResponse.json({ ok: true });
}
