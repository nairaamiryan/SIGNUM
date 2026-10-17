import { ERROR_MESSAGES } from "@/lib/constants";
import { NextResponse } from "next/server";
import { z } from "zod";
import { User } from "@/lib/db";
import { getUserId } from "@/lib/session-auth";

const attributes = ["id", "email", "name", "createdAt"];

export async function GET(req: Request) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });

  const user = await User.findByPk(userId, { attributes });
  if (!user) return NextResponse.json({ error: ERROR_MESSAGES.NOT_FOUND }, { status: 404 });
  return NextResponse.json(user);
}

const patchSchema = z.object({ name: z.string().min(1).max(100) });

export async function PATCH(req: Request) {
  const userId = getUserId(req);
  if (!userId) return NextResponse.json({ error: ERROR_MESSAGES.UNAUTHORIZED }, { status: 401 });

  const parsed = patchSchema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
  }
  const user = await User.findByPk(userId);
  if (!user) return NextResponse.json({ error: ERROR_MESSAGES.NOT_FOUND }, { status: 404 });
  await user.update(parsed.data);
  const u = user.get() as { id: string; email: string; name: string; createdAt: Date };
  return NextResponse.json({ id: u.id, email: u.email, name: u.name, createdAt: u.createdAt });
}
