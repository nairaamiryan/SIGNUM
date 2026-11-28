"use client";

import {
    createContext,
    useContext,
    useEffect,
    useMemo,
    useSyncExternalStore,
    type ReactNode,
} from "react";
import {
    AuthRequestError,
    fetchCurrentUser,
    googleLoginRequest,
    loginRequest,
    registerRequest,
} from "@/lib/authClient";
import {
    clearSession,
    parseSession,
    readRawSession,
    saveSession,
    subscribeSession,
} from "@/lib/authStorage";
import type { LoginFormValues, RegisterFormValues } from "@/lib/schemas";
import type { AuthUser } from "@/lib/types";
import { HttpStatus } from "@/lib/constants";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
    status: AuthStatus;
    user: AuthUser | null;
    login: (values: LoginFormValues) => Promise<AuthUser>;
    register: (values: RegisterFormValues) => Promise<AuthUser>;
    loginWithGoogle: (credential: string) => Promise<AuthUser>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const subscribeNever = () => () => {};

async function login(values: LoginFormValues): Promise<AuthUser> {
    const session = await loginRequest(values);
    saveSession(session);
    return session.user;
}

async function register(values: RegisterFormValues): Promise<AuthUser> {
    const session = await registerRequest(values);
    saveSession(session);
    return session.user;
}

async function loginWithGoogle(credential: string): Promise<AuthUser> {
    const session = await googleLoginRequest(credential);
    saveSession(session);
    return session.user;
}

export function AuthProvider({ children }: { children: ReactNode }) {
    // The session lives in localStorage; this store has no value on the server.
    const raw = useSyncExternalStore(subscribeSession, readRawSession, () => null);
    // False while rendering on the server and during hydration, so the first
    // client render matches the server HTML.
    const hydrated = useSyncExternalStore(
        subscribeNever,
        () => true,
        () => false,
    );

    const session = useMemo(() => parseSession(raw), [raw]);
    const token = session?.token ?? null;

    // Check the stored token once and refresh the profile. An expired or
    // revoked token signs the user out.
    useEffect(() => {
        if (!token) return;
        let cancelled = false;

        fetchCurrentUser(token)
            .then((user) => {
                if (!cancelled) saveSession({ token, user });
            })
            .catch((error: unknown) => {
                if (
                    !cancelled &&
                    error instanceof AuthRequestError &&
                    error.status === HttpStatus.UNAUTHORIZED
                ) {
                    clearSession();
                }
            });

        return () => {
            cancelled = true;
        };
    }, [token]);

    const value = useMemo<AuthContextValue>(
        () => ({
            status: !hydrated ? "loading" : session ? "authenticated" : "unauthenticated",
            user: session?.user ?? null,
            login,
            register,
            loginWithGoogle,
            logout: clearSession,
        }),
        [hydrated, session],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used inside <AuthProvider>");
    }
    return context;
}
