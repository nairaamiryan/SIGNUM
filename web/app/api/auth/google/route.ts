import { NextResponse } from "next/server";
import { OAuth2Client, type TokenPayload } from "google-auth-library";
import { signToken } from "@/lib/auth";
import { ERROR_MESSAGES } from "@/lib/constants";
import { findOrCreateGoogleUser } from "@/lib/google-user";
import { logger } from "@/lib/logger";
import { googleAuthSchema } from "@/lib/schemas";
import { toPublicUser } from "@/lib/user-dto";

// The same OAuth client ID is used by the browser button and to verify the token.
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export async function POST(req: Request) {
    if (!GOOGLE_CLIENT_ID) {
        return NextResponse.json({ error: ERROR_MESSAGES.GOOGLE_NOT_CONFIGURED }, { status: 503 });
    }

    const parsed = googleAuthSchema.safeParse(await req.json().catch(() => null));
    if (!parsed.success) {
        return NextResponse.json({ error: ERROR_MESSAGES.INVALID_INPUT }, { status: 400 });
    }

    // Checks the signature, the expiry and that the token was issued for this app.
    let payload: TokenPayload | undefined;
    try {
        const ticket = await new OAuth2Client().verifyIdToken({
            idToken: parsed.data.credential,
            audience: GOOGLE_CLIENT_ID,
        });
        payload = ticket.getPayload();
    } catch {
        logger.warn("APP", "Rejected Google ID token", { audit: true });
        return NextResponse.json({ error: ERROR_MESSAGES.GOOGLE_AUTH_FAILED }, { status: 401 });
    }

    if (!payload?.sub || !payload.email) {
        return NextResponse.json({ error: ERROR_MESSAGES.GOOGLE_AUTH_FAILED }, { status: 401 });
    }
    if (!payload.email_verified) {
        return NextResponse.json(
            { error: ERROR_MESSAGES.GOOGLE_EMAIL_NOT_VERIFIED },
            { status: 401 },
        );
    }

    const user = await findOrCreateGoogleUser(payload);

    logger.info("APP", `User ${user.id} signed in with Google`, { audit: true });
    return NextResponse.json({ token: signToken(user.id), user: toPublicUser(user) });
}
