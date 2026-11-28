import { z } from "zod";
import { NAME_MAX_LENGTH, PASSWORD_MIN_LENGTH } from "./constants";

export const registerSchema = z.object({
    email: z.string().email(),
    password: z.string().min(PASSWORD_MIN_LENGTH),
    name: z.string().optional(),
});

export const loginSchema = z.object({
    email: z.string().email(),
    password: z.string(),
});

export const googleAuthSchema = z.object({
    // ID token (JWT) issued by Google Identity Services.
    credential: z.string().min(1),
});

export const updateUserSchema = z.object({
    name: z.string().min(1).max(100),
});

export const captionSchema = z.object({
    text: z.string().min(1),
    glosses: z.array(z.string()).default([]),
    confidence: z.number().min(0).max(1).optional(),
});

export const gestureSchema = z.object({
    gloss: z.string().min(1),
    classId: z.number().int().optional(),
    confidence: z.number().min(0).max(1),
    landmarkData: z.any().optional(),
});

export const logSchema = z.object({
    level: z.enum(["DEBUG", "INFO", "WARN", "ERROR"]),
    message: z.string().min(1).max(2000),
    audit: z.boolean().optional(),
    sessionId: z.string().nullable().optional(),
});

// Form schemas used by the login and registration pages. Their messages are
// i18n keys, translated where the error is rendered.
const emailField = z
    .string()
    .trim()
    .min(1, "auth.validation.emailRequired")
    .email("auth.validation.emailInvalid");

export const loginFormSchema = z.object({
    email: emailField,
    password: z.string().min(1, "auth.validation.passwordRequired"),
});

export const registerFormSchema = z
    .object({
        name: z
            .string()
            .trim()
            .min(1, "auth.validation.nameRequired")
            .max(NAME_MAX_LENGTH, "auth.validation.nameTooLong"),
        email: emailField,
        password: z.string().min(PASSWORD_MIN_LENGTH, "auth.validation.passwordTooShort"),
        confirmPassword: z.string().min(1, "auth.validation.confirmRequired"),
    })
    .refine((values) => values.password === values.confirmPassword, {
        path: ["confirmPassword"],
        message: "auth.validation.passwordsMismatch",
    });

export type LoginFormValues = z.infer<typeof loginFormSchema>;
export type RegisterFormValues = z.infer<typeof registerFormSchema>;
