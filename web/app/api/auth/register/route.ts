import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { User } from "@/lib/db";
import { signToken } from "@/lib/auth";
import { registerSchema } from "@/lib/schemas";
import { ERROR_MESSAGES } from "@/lib/constants";
import { logger } from "@/lib/logger";
import { toPublicUser, type UserRecord } from "@/lib/user-dto";

export async function POST(req: Request) {
    const parsed = registerSchema.safeParse(await req.json());
    if (!parsed.success) {
        return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
    }
    const { email, password, name } = parsed.data;

    const exists = await User.findOne({ where: { email } });
    if (exists) {
        return NextResponse.json(
            { error: ERROR_MESSAGES.EMAIL_ALREADY_REGISTERED },
            { status: 409 },
        );
    }

    const user = await User.create({
        email,
        name,
        passwordHash: await bcrypt.hash(password, 10),
    });
    const u = user.get() as UserRecord;

    logger.info("APP", `User ${u.id} registered`, { audit: true });
    return NextResponse.json({ token: signToken(u.id), user: toPublicUser(u) }, { status: 201 });
}
