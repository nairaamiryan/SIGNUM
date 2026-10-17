import { ERROR_MESSAGES } from "@/lib/constants";
import { NextResponse } from "next/server";
import { RecognitionSession, Caption } from "@/lib/db";
import { getUserId } from "@/lib/session-auth";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });

  const { id } = await params;
  const session = await RecognitionSession.findOne({ where: { id, userId } });
  if (!session) return NextResponse.json({ error: ERROR_MESSAGES.NOT_FOUND }, { status: 404 });

  const captions = await Caption.findAll({
    where: { sessionId: id },
    order: [["createdAt", "ASC"]],
  });
  return NextResponse.json(captions);
}
