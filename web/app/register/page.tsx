"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import RegisterForm from "@/components/auth/RegisterForm";
import { AppRoute } from "@/lib/constants";

export default function RegisterPage() {
    const router = useRouter();
    const { status } = useAuth();

    // A signed-in user (also right after a successful submit) goes to the main page.
    useEffect(() => {
        if (status === "authenticated") router.replace(AppRoute.HOME);
    }, [status, router]);

    return <RegisterForm />;
}
