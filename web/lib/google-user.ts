import type { TokenPayload } from "google-auth-library";
import { Op } from "sequelize";
import { sequelize, User } from "@/lib/db";
import { AuthProviderName } from "@/lib/constants";
import type { UserRecord } from "@/lib/user-dto";

type GoogleProfile = Pick<TokenPayload, "sub" | "email" | "name" | "picture">;

type StoredUser = UserRecord & { googleId: string | null };

/**
 * Finds the account of a verified Google profile, or creates it.
 * An existing account with the same email is linked to the Google account, so
 * a person who registered with a password can later use Google as well.
 */
export async function findOrCreateGoogleUser(profile: GoogleProfile): Promise<UserRecord> {
    const email = profile.email as string;
    const googleId = profile.sub;
    const avatarUrl = profile.picture ?? null;

    const found =
        (await User.findOne({ where: { googleId } })) ??
        (await User.findOne({
            where: {
                [Op.and]: [
                    sequelize.where(
                        sequelize.fn("lower", sequelize.col("email")),
                        email.toLowerCase(),
                    ),
                ],
            },
        }));

    if (found) {
        const existing = found.get() as StoredUser;
        const updates: Record<string, unknown> = {};
        if (!existing.googleId) updates.googleId = googleId;
        if (!existing.avatarUrl && avatarUrl) updates.avatarUrl = avatarUrl;
        if (!existing.name && profile.name) updates.name = profile.name;
        if (Object.keys(updates).length > 0) await found.update(updates);
        return found.get() as UserRecord;
    }

    const created = await User.create({
        email,
        name: profile.name ?? null,
        googleId,
        avatarUrl,
        authProvider: AuthProviderName.GOOGLE,
        passwordHash: null,
    });
    return created.get() as UserRecord;
}
