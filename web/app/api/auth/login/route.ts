import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { User } from "@/lib/db";
import { signToken } from "@/lib/auth";
import { loginSchema } from "@/lib/schemas";
import { ERROR_MESSAGES } from "@/lib/constants";

export async function POST(req: Request) {
  const parsed = loginSchema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
  }
  const { email, password } = parsed.data;

  const found = await User.findOne({ where: { email } });
  const u = found?.get() as
    | { id: string; email: string; name: string | null; passwordHash: string }
    | undefined;
  if (!u || !(await bcrypt.compare(password, u.passwordHash))) {
    return NextResponse.json({ error: ERROR_MESSAGES.INVALID_CREDENTIALS }, { status: 401 });
  }

  return NextResponse.json({
    token: signToken(u.id),
    user: { id: u.id, email: u.email, name: u.name },
  });
}
