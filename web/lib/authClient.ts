import { ApiRoute, ERROR_MESSAGES, HttpStatus } from "./constants";
import type { AuthSession, AuthUser } from "./types";
import type { LoginFormValues, RegisterFormValues } from "./schemas";

export class AuthRequestError extends Error {
    constructor(public readonly status: number) {
        super(ERROR_MESSAGES.AUTH_REQUEST_FAILED);
        this.name = "AuthRequestError";
    }
}

function toAuthUser(data: Partial<AuthUser> & { id: string; email: string }): AuthUser {
    return {
        id: data.id,
        email: data.email,
        name: data.name ?? null,
        avatarUrl: data.avatarUrl ?? null,
    };
}

async function request<T>(url: string, init: RequestInit): Promise<T> {
    const response = await fetch(url, init);
    if (!response.ok) throw new AuthRequestError(response.status);
    return (await response.json()) as T;
}

function postJson(url: string, body: unknown): Promise<{ token: string; user: AuthUser }> {
    return request(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

async function toSession(result: Promise<{ token: string; user: AuthUser }>): Promise<AuthSession> {
    const { token, user } = await result;
    return { token, user: toAuthUser(user) };
}

export function loginRequest(values: LoginFormValues): Promise<AuthSession> {
    return toSession(postJson(ApiRoute.LOGIN, values));
}

export function registerRequest(values: RegisterFormValues): Promise<AuthSession> {
    const { name, email, password } = values;
    return toSession(postJson(ApiRoute.REGISTER, { name, email, password }));
}

export function googleLoginRequest(credential: string): Promise<AuthSession> {
    return toSession(postJson(ApiRoute.GOOGLE, { credential }));
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
    const data = await request<Partial<AuthUser> & { id: string; email: string }>(ApiRoute.ME, {
        headers: { Authorization: `Bearer ${token}` },
    });
    return toAuthUser(data);
}

export type AuthMethod = "password" | "google";

/** i18n key of the message that explains an authentication failure to the user. */
export function authErrorKey(error: unknown, method: AuthMethod): string {
    if (error instanceof AuthRequestError) {
        switch (error.status) {
            case HttpStatus.BAD_REQUEST:
                return "auth.errors.invalidInput";
            case HttpStatus.UNAUTHORIZED:
                return method === "google"
                    ? "auth.errors.googleFailed"
                    : "auth.errors.invalidCredentials";
            case HttpStatus.CONFLICT:
                return "auth.errors.emailTaken";
            case HttpStatus.SERVICE_UNAVAILABLE:
                return method === "google"
                    ? "auth.errors.googleUnavailable"
                    : "auth.errors.generic";
            default:
                return "auth.errors.generic";
        }
    }
    // fetch() rejects with a TypeError when the server cannot be reached.
    if (error instanceof TypeError) return "auth.errors.network";
    return "auth.errors.generic";
}
