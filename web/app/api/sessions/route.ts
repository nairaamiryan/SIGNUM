import { ERROR_MESSAGES } from "@/lib/constants";
import { NextResponse } from "next/server";
import { RecognitionSession, Caption } from "@/lib/db";
import { getUserId } from "@/lib/session-auth";

export async function POST(req: Request) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });

  const session = await RecognitionSession.create({ userId });
  return NextResponse.json(session, { status: 201 });
}

export async function GET(req: Request) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });

  const sessions = await RecognitionSession.findAll({
    where: { userId },
    order: [["startedAt", "DESC"]],
  });
  const result = await Promise.all(
    sessions.map(async (s) => ({
      ...s.get(),
      captionCount: await Caption.count({ where: { sessionId: s.get("id") as string } }),
    }))
  );
  return NextResponse.json(result);
}
