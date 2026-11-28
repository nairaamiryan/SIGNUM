"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { LogIn } from "lucide-react";
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
import { AppRoute } from "@/lib/constants";
import { loginFormSchema, type LoginFormValues } from "@/lib/schemas";

export default function LoginForm() {
    const { t } = useTranslation();
    const { login } = useAuth();
    const [errorKey, setErrorKey] = useState<string | null>(null);

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
    } = useForm<LoginFormValues>({
        resolver: zodResolver(loginFormSchema),
        defaultValues: { email: "", password: "" },
    });

    const onSubmit = async (values: LoginFormValues) => {
        setErrorKey(null);
        try {
            const user = await login(values);
            toast.success(t("auth.welcomeBack", { name: user.name ?? user.email }));
        } catch (error) {
            setErrorKey(authErrorKey(error, "password"));
        }
    };

    return (
        <AuthShell
            title={t("auth.login.title")}
            description={t("auth.login.description")}
            footer={
                <span>
                    {t("auth.login.noAccount")}{" "}
                    <Link
                        href={AppRoute.REGISTER}
                        className="font-medium text-primary hover:underline"
                    >
                        {t("auth.login.toRegister")}
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
                    id="login-email"
                    label={t("auth.fields.email")}
                    error={errors.email?.message && t(errors.email.message)}
                >
                    <Input
                        id="login-email"
                        type="email"
                        autoComplete="email"
                        placeholder={t("auth.fields.emailPlaceholder")}
                        aria-invalid={!!errors.email}
                        aria-describedby={errors.email ? "login-email-error" : undefined}
                        {...register("email")}
                    />
                </FormField>

                <FormField
                    id="login-password"
                    label={t("auth.fields.password")}
                    error={errors.password?.message && t(errors.password.message)}
                >
                    <PasswordInput
                        id="login-password"
                        autoComplete="current-password"
                        aria-invalid={!!errors.password}
                        aria-describedby={errors.password ? "login-password-error" : undefined}
                        {...register("password")}
                    />
                </FormField>

                <Button type="submit" disabled={isSubmitting}>
                    <LogIn />
                    {isSubmitting ? t("auth.login.submitting") : t("auth.login.submit")}
                </Button>
            </form>

            <GoogleAuthSection onError={setErrorKey} />
        </AuthShell>
    );
}
