import { NextResponse } from "next/server";
import { z } from "zod";
import { RecognitionSession, RecognizedGesture } from "@/lib/db";
import { isServiceRequest } from "@/lib/service-auth";

const schema = z.object({
  gloss: z.string().min(1),
  classId: z.number().int().optional(),
  confidence: z.number().min(0).max(1),
  landmarkData: z.any().optional(),
});

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!isServiceRequest(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { id } = await params;
  const parsed = schema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }
  const session = await RecognitionSession.findByPk(id);
  if (!session) return NextResponse.json({ error: "Session not found" }, { status: 404 });

  const gesture = await RecognizedGesture.create({ sessionId: id, ...parsed.data });
  return NextResponse.json(gesture, { status: 201 });
}
