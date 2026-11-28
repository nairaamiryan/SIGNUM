"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import LoginForm from "@/components/auth/LoginForm";
import { AppRoute } from "@/lib/constants";

export default function LoginPage() {
    const router = useRouter();
    const { status } = useAuth();

    // A signed-in user (also right after a successful submit) goes to the main page.
    useEffect(() => {
        if (status === "authenticated") router.replace(AppRoute.HOME);
    }, [status, router]);

    return <LoginForm />;
}
