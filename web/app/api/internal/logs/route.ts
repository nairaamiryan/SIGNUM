import { NextResponse } from "next/server";
import { isServiceRequest } from "@/lib/service-auth";
import { log } from "@/lib/logger";
import { logSchema } from "@/lib/schemas";
import { ERROR_MESSAGES } from "@/lib/constants";

// Receives log lines from the Python gesture service so that all components
// write to the same single log file.
export async function POST(req: Request) {
  if (!isServiceRequest(req)) {
    return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });
  }
  const parsed = logSchema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
  }
  const { level, message, audit, sessionId } = parsed.data;
  log(level, "GESTURE_SERVICE", message, { audit, sessionId });
  return NextResponse.json({ ok: true }, { status: 201 });
}
