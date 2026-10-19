import { NextResponse } from "next/server";
import { isServiceRequest } from "@/lib/service-auth";
import { findSessionById } from "@/lib/repositories/sessions";
import { createCaption } from "@/lib/repositories/captions";
import { captionSchema } from "@/lib/schemas";
import { ERROR_MESSAGES } from "@/lib/constants";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!isServiceRequest(req)) {
    return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });
  }
  const { id } = await params;
  const parsed = captionSchema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
  }
  if (!(await findSessionById(id))) {
    return NextResponse.json({ error: ERROR_MESSAGES.SESSION_NOT_FOUND }, { status: 404 });
  }
  return NextResponse.json(await createCaption(id, parsed.data), { status: 201 });
}
