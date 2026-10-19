import { NextResponse } from "next/server";
import { getUserId } from "@/lib/session-auth";
import { findUserSession } from "@/lib/repositories/sessions";
import { listCaptions } from "@/lib/repositories/captions";
import { ERROR_MESSAGES } from "@/lib/constants";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });

  const { id } = await params;
  if (!(await findUserSession(id, userId))) {
    return NextResponse.json({ error: ERROR_MESSAGES.NOT_FOUND }, { status: 404 });
  }
  return NextResponse.json(await listCaptions(id));
}
