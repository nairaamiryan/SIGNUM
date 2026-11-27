export interface UserRecord {
    id: string;
    email: string;
    name: string | null;
    avatarUrl?: string | null;
}

/** The user fields that are safe to return to the browser. */
export function toPublicUser(user: UserRecord) {
    return {
        id: user.id,
        email: user.email,
        name: user.name,
        avatarUrl: user.avatarUrl ?? null,
    };
}
