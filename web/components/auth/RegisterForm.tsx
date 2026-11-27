"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { UserPlus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { useAuth } from "@/components/AuthProvider";
import AuthShell from "@/components/auth/AuthShell";
import FormField from "@/components/auth/FormField";
import GoogleAuthSection from "@/components/auth/GoogleAuthSection";
import PasswordInput from "@/components/auth/PasswordInput";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authErrorKey } from "@/lib/authClient";
import { AppRoute, PASSWORD_MIN_LENGTH } from "@/lib/constants";
import { registerFormSchema, type RegisterFormValues } from "@/lib/schemas";

export default function RegisterForm() {
    const { t } = useTranslation();
    const { register: registerUser } = useAuth();
    const [errorKey, setErrorKey] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<RegisterFormValues>({
        resolver: zodResolver(registerFormSchema),
        defaultValues: { name: "", email: "", password: "", confirmPassword: "" },
    });

    // Validation messages are i18n keys; the password rule needs its length.
    const message = (key: string | undefined) =>
        key ? t(key, { count: PASSWORD_MIN_LENGTH }) : undefined;

    const onSubmit = async (values: RegisterFormValues) => {
        setErrorKey(null);
        try {
            const user = await registerUser(values);
            toast.success(t("auth.register.success", { name: user.name ?? user.email }));
        } catch (error) {
            setErrorKey(authErrorKey(error, "password"));
        }
    };

    return (
        <AuthShell
            title={t("auth.register.title")}
            description={t("auth.register.description")}
            footer={
                <span>
                    {t("auth.register.haveAccount")}{" "}
                    <Link
                        href={AppRoute.LOGIN}
                        className="font-medium text-primary hover:underline"
                    >
                        {t("auth.register.toLogin")}
                    </Link>
                </span>
            }
        >
            {errorKey && (
                <Alert variant="destructive">
                    <AlertDescription>{t(errorKey)}</AlertDescription>
                </Alert>
            )}

            <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
                <FormField
                    id="register-name"
                    label={t("auth.fields.name")}
                    error={message(errors.name?.message)}
                >
                    <Input
                        id="register-name"
                        autoComplete="name"
                        placeholder={t("auth.fields.namePlaceholder")}
                        aria-invalid={!!errors.name}
                        aria-describedby={errors.name ? "register-name-error" : undefined}
                        {...register("name")}
                    />
                </FormField>

                <FormField
                    id="register-email"
                    label={t("auth.fields.email")}
                    error={message(errors.email?.message)}
                >
                    <Input
                        id="register-email"
                        type="email"
                        autoComplete="email"
                        placeholder={t("auth.fields.emailPlaceholder")}
                        aria-invalid={!!errors.email}
                        aria-describedby={errors.email ? "register-email-error" : undefined}
                        {...register("email")}
                    />
                </FormField>

                <FormField
                    id="register-password"
                    label={t("auth.fields.password")}
                    error={message(errors.password?.message)}
                >
                    <PasswordInput
                        id="register-password"
                        autoComplete="new-password"
                        aria-invalid={!!errors.password}
                        aria-describedby={errors.password ? "register-password-error" : undefined}
                        {...register("password")}
                    />
                </FormField>

                <FormField
                    id="register-confirm"
                    label={t("auth.fields.confirmPassword")}
                    error={message(errors.confirmPassword?.message)}
                >
                    <PasswordInput
                        id="register-confirm"
                        autoComplete="new-password"
                        aria-invalid={!!errors.confirmPassword}
                        aria-describedby={
                            errors.confirmPassword ? "register-confirm-error" : undefined
                        }
                        {...register("confirmPassword")}
                    />
                </FormField>

                <Button type="submit" disabled={isSubmitting}>
                    <UserPlus />
                    {isSubmitting ? t("auth.register.submitting") : t("auth.register.submit")}
                </Button>
            </form>

            <GoogleAuthSection onError={setErrorKey} />
        </AuthShell>
    );
}
