import { NextResponse } from "next/server";
import { z } from "zod";
import { isServiceRequest } from "@/lib/service-auth";
import { findSessionById } from "@/lib/repositories/sessions";
import { createCaption } from "@/lib/repositories/captions";
import { ERROR_MESSAGES } from "@/lib/constants";

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
  if (!(await findSessionById(id))) {
    return NextResponse.json({ error: ERROR_MESSAGES.SESSION_NOT_FOUND }, { status: 404 });
  }
  return NextResponse.json(await createCaption(id, parsed.data), { status: 201 });
}
