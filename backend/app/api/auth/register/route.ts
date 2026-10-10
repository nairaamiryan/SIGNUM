import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { signToken } from "@/lib/auth";

const schema = z.object({
    email: z.string().email(),
    password: z.string().min(8),
    name: z.string().optional(),
});

export async function POST(req: Request) {
    const parsed = schema.safeParse(await req.json());
    if (!parsed.success) {
        return NextResponse.json({ error: "Invalid input" }, { status: 400 });
    }
    const { email, password, name } = parsed.data;

    const exists = await prisma.user.findUnique({ where: { email } });
    if (exists) {
        return NextResponse.json({ error: "Email already registered" }, { status: 409 });
    }

    const user = await prisma.user.create({
        data: { email, name, passwordHash: await bcrypt.hash(password, 10) },
    });

    return NextResponse.json(
        { token: signToken(user.id), user: { id: user.id, email: user.email, name: user.name } },
        { status: 201 }
    );
}