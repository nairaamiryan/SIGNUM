import { ERROR_MESSAGES } from "@/lib/constants";
import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { User } from "@/lib/db";
import { signToken } from "@/lib/auth";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().optional(),
});

export async function POST(req: Request) {
  const parsed = schema.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
  }
  const { email, password, name } = parsed.data;

  const exists = await User.findOne({ where: { email } });
  if (exists) {
    return NextResponse.json({ error: ERROR_MESSAGES.EMAIL_ALREADY_REGISTERED }, { status: 409 });
  }

  const user = await User.create({
    email,
    name,
    passwordHash: await bcrypt.hash(password, 10),
  });
  const u = user.get() as { id: string; email: string; name: string | null };

  return NextResponse.json(
    { token: signToken(u.id), user: { id: u.id, email: u.email, name: u.name } },
    { status: 201 }
  );
}
