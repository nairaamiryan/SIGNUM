import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthRequestError, authErrorKey, googleLoginRequest, loginRequest } from "./authClient";
import { ApiRoute } from "./constants";

function mockFetch(status: number, body: unknown = {}) {
    const fetchMock = vi.fn().mockResolvedValue({
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
}

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("auth requests", () => {
    it("sends the credentials and returns the session", async () => {
        const fetchMock = mockFetch(200, {
            token: "jwt",
            user: { id: "1", email: "a@b.am", name: null },
        });

        const session = await loginRequest({ email: "a@b.am", password: "secret" });

        expect(fetchMock).toHaveBeenCalledWith(
            ApiRoute.LOGIN,
            expect.objectContaining({ method: "POST" }),
        );
        expect(session).toEqual({
            token: "jwt",
            user: { id: "1", email: "a@b.am", name: null, avatarUrl: null },
        });
    });

    it("sends the Google credential", async () => {
        const fetchMock = mockFetch(200, { token: "jwt", user: { id: "1", email: "a@b.am" } });
        await googleLoginRequest("google-id-token");
        const init = fetchMock.mock.calls[0][1] as RequestInit;
        expect(fetchMock.mock.calls[0][0]).toBe(ApiRoute.GOOGLE);
        expect(JSON.parse(init.body as string)).toEqual({ credential: "google-id-token" });
    });

    it("throws an AuthRequestError with the HTTP status", async () => {
        mockFetch(401);
        await expect(loginRequest({ email: "a@b.am", password: "x" })).rejects.toMatchObject({
            name: "AuthRequestError",
            status: 401,
        });
    });
});

describe("authErrorKey", () => {
    it("explains wrong credentials for a password login", () => {
        expect(authErrorKey(new AuthRequestError(401), "password")).toBe(
            "auth.errors.invalidCredentials",
        );
    });

    it("explains a Google failure separately", () => {
        expect(authErrorKey(new AuthRequestError(401), "google")).toBe("auth.errors.googleFailed");
        expect(authErrorKey(new AuthRequestError(503), "google")).toBe(
            "auth.errors.googleUnavailable",
        );
    });

    it("maps the other statuses", () => {
        expect(authErrorKey(new AuthRequestError(409), "password")).toBe("auth.errors.emailTaken");
        expect(authErrorKey(new AuthRequestError(400), "password")).toBe(
            "auth.errors.invalidInput",
        );
        expect(authErrorKey(new AuthRequestError(500), "password")).toBe("auth.errors.generic");
    });

    it("recognizes a network failure", () => {
        expect(authErrorKey(new TypeError("Failed to fetch"), "password")).toBe(
            "auth.errors.network",
        );
    });
});
