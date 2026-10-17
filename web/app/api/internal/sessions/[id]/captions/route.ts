import { ERROR_MESSAGES } from "@/lib/constants";
import { NextResponse } from "next/server";
import { z } from "zod";
import { RecognitionSession, Caption } from "@/lib/db";
import { isServiceRequest } from "@/lib/service-auth";

const schema = z.object({
  text: z.string().min(1),
  glosses: z.array(z.string()).default([]),
  confidence: z.number().min(0).max(1).optional(),
});

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!isServiceRequest(req)) {
    return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });
  }
  const { id } = await params;
  const parsed = schema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
  }
  const session = await RecognitionSession.findByPk(id);
  if (!session) return NextResponse.json({ error: ERROR_MESSAGES.SESSION_NOT_FOUND }, { status: 404 });

  const caption = await Caption.create({ sessionId: id, ...parsed.data });
  return NextResponse.json(caption, { status: 201 });
}
