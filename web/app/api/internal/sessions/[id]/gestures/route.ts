import { NextResponse } from "next/server";
import { isServiceRequest } from "@/lib/service-auth";
import { findSessionById } from "@/lib/repositories/sessions";
import { createGesture } from "@/lib/repositories/captions";
import { gestureSchema } from "@/lib/schemas";
import { ERROR_MESSAGES } from "@/lib/constants";

// Raw landmark sequences are high-volume; store them only when explicitly enabled
// (training, debugging or dataset generation).
const STORE_LANDMARKS = process.env.STORE_LANDMARKS === "true";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!isServiceRequest(req)) {
    return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });
  }
  const { id } = await params;
  const parsed = gestureSchema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
  }
  if (!(await findSessionById(id))) {
    return NextResponse.json({ error: ERROR_MESSAGES.SESSION_NOT_FOUND }, { status: 404 });
  }
  const { landmarkData, ...rest } = parsed.data;
  const gesture = await createGesture(id, {
    ...rest,
    ...(STORE_LANDMARKS && landmarkData !== undefined ? { landmarkData } : {}),
  });
  return NextResponse.json(gesture, { status: 201 });
}
