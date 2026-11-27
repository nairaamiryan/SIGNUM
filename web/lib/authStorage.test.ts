import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AUTH_STORAGE_KEY } from "./constants";
import {
    clearSession,
    parseSession,
    readRawSession,
    saveSession,
    subscribeSession,
} from "./authStorage";

const session = {
    token: "jwt",
    user: { id: "1", email: "a@b.am", name: "Naira", avatarUrl: null },
};

describe("parseSession", () => {
    it("returns the stored session", () => {
        expect(parseSession(JSON.stringify(session))).toEqual(session);
    });

    it("returns null for empty or broken values", () => {
        expect(parseSession(null)).toBeNull();
        expect(parseSession("")).toBeNull();
        expect(parseSession("{not json")).toBeNull();
        expect(parseSession("42")).toBeNull();
        expect(parseSession(JSON.stringify({ token: "", user: session.user }))).toBeNull();
        expect(parseSession(JSON.stringify({ token: "t", user: { id: 1 } }))).toBeNull();
    });

    it("fills missing optional user fields with null", () => {
        const raw = JSON.stringify({ token: "t", user: { id: "1", email: "a@b.am" } });
        expect(parseSession(raw)?.user).toEqual({
            id: "1",
            email: "a@b.am",
            name: null,
            avatarUrl: null,
        });
    });
});

describe("session storage", () => {
    const data = new Map<string, string>();
    const windowEvents = new EventTarget();

    beforeEach(() => {
        data.clear();
        vi.stubGlobal("localStorage", {
            getItem: (key: string) => data.get(key) ?? null,
            setItem: (key: string, value: string) => void data.set(key, value),
            removeItem: (key: string) => void data.delete(key),
        });
        vi.stubGlobal("window", windowEvents);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("saves, reads and clears the session", () => {
        saveSession(session);
        expect(JSON.parse(readRawSession() as string)).toEqual(session);
        expect(data.has(AUTH_STORAGE_KEY)).toBe(true);

        clearSession();
        expect(readRawSession()).toBeNull();
    });

    it("notifies subscribers about changes until they unsubscribe", () => {
        const listener = vi.fn();
        const unsubscribe = subscribeSession(listener);

        saveSession(session);
        clearSession();
        expect(listener).toHaveBeenCalledTimes(2);

        unsubscribe();
        saveSession(session);
        expect(listener).toHaveBeenCalledTimes(2);
    });

    it("does not throw when localStorage is unavailable", () => {
        vi.stubGlobal("localStorage", {
            getItem: () => {
                throw new Error("blocked");
            },
            setItem: () => {
                throw new Error("blocked");
            },
            removeItem: () => {
                throw new Error("blocked");
            },
        });
        expect(readRawSession()).toBeNull();
        expect(() => saveSession(session)).not.toThrow();
        expect(() => clearSession()).not.toThrow();
    });
});
