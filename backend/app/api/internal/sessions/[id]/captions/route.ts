import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
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
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { id } = await params;
  const parsed = schema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }
  const session = await prisma.recognitionSession.findUnique({ where: { id } });
  if (!session) return NextResponse.json({ error: "Session not found" }, { status: 404 });

  const caption = await prisma.caption.create({ data: { sessionId: id, ...parsed.data } });
  return NextResponse.json(caption, { status: 201 });
}
