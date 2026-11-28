import { describe, expect, it } from "vitest";
import { googleAuthSchema, loginFormSchema, registerFormSchema, registerSchema } from "./schemas";

const validRegistration = {
    name: "Naira",
    email: "naira@example.com",
    password: "password123",
    confirmPassword: "password123",
};

function firstMessage(result: { success: boolean; error?: { issues: { message: string }[] } }) {
    return result.error?.issues[0]?.message;
}

describe("loginFormSchema", () => {
    it("accepts an email and a password", () => {
        expect(loginFormSchema.safeParse({ email: "a@b.am", password: "x" }).success).toBe(true);
    });

    it("asks for the email when it is empty", () => {
        const result = loginFormSchema.safeParse({ email: "  ", password: "x" });
        expect(firstMessage(result)).toBe("auth.validation.emailRequired");
    });

    it("rejects an invalid email", () => {
        const result = loginFormSchema.safeParse({ email: "not-an-email", password: "x" });
        expect(firstMessage(result)).toBe("auth.validation.emailInvalid");
    });

    it("asks for the password when it is empty", () => {
        const result = loginFormSchema.safeParse({ email: "a@b.am", password: "" });
        expect(firstMessage(result)).toBe("auth.validation.passwordRequired");
    });
});

describe("registerFormSchema", () => {
    it("accepts valid values", () => {
        expect(registerFormSchema.safeParse(validRegistration).success).toBe(true);
    });

    it("requires a name", () => {
        const result = registerFormSchema.safeParse({ ...validRegistration, name: " " });
        expect(firstMessage(result)).toBe("auth.validation.nameRequired");
    });

    it("rejects a short password", () => {
        const result = registerFormSchema.safeParse({
            ...validRegistration,
            password: "short",
            confirmPassword: "short",
        });
        expect(firstMessage(result)).toBe("auth.validation.passwordTooShort");
    });

    it("reports different passwords on the confirmation field", () => {
        const result = registerFormSchema.safeParse({
            ...validRegistration,
            confirmPassword: "different123",
        });
        expect(result.success).toBe(false);
        const issue = result.error?.issues[0];
        expect(issue?.message).toBe("auth.validation.passwordsMismatch");
        expect(issue?.path).toEqual(["confirmPassword"]);
    });
});

describe("API schemas", () => {
    it("keeps the name optional on the server", () => {
        expect(registerSchema.safeParse({ email: "a@b.am", password: "password123" }).success).toBe(
            true,
        );
    });

    it("requires a credential for Google sign-in", () => {
        expect(googleAuthSchema.safeParse({}).success).toBe(false);
        expect(googleAuthSchema.safeParse({ credential: "" }).success).toBe(false);
        expect(googleAuthSchema.safeParse({ credential: "token" }).success).toBe(true);
    });
});
