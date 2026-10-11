import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { User } from "@/lib/db";
import { signToken } from "@/lib/auth";

const schema = z.object({ email: z.string().email(), password: z.string() });

export async function POST(req: Request) {
  const parsed = schema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 });
  }
  const { email, password } = parsed.data;

  const found = await User.findOne({ where: { email } });
  const u = found?.get() as
    | { id: string; email: string; name: string | null; passwordHash: string }
    | undefined;
  if (!u || !(await bcrypt.compare(password, u.passwordHash))) {
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }

  return NextResponse.json({
    token: signToken(u.id),
    user: { id: u.id, email: u.email, name: u.name },
  });
}
