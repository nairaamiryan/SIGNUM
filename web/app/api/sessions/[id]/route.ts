import { ERROR_MESSAGES } from "@/lib/constants";
import { NextResponse } from "next/server";
import { RecognitionSession } from "@/lib/db";
import { getUserId } from "@/lib/session-auth";

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });

  const { id } = await params;
  const [count] = await RecognitionSession.update(
    { status: "ENDED", endedAt: new Date() },
    { where: { id, userId } }
  );
  if (count === 0) return NextResponse.json({ error: ERROR_MESSAGES.NOT_FOUND }, { status: 404 });
  return NextResponse.json({ ok: true });
}
