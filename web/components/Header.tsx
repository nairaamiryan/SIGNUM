"use client";

import Link from "next/link";
import { Hand } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/components/AuthProvider";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import UserMenu from "@/components/UserMenu";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { APP_NAME, AppRoute } from "@/lib/constants";

export default function Header() {
    const { t } = useTranslation();
    const { status, user } = useAuth();

    return (
        <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-3 px-4">
                <Link
                    href={AppRoute.HOME}
                    className="flex items-center gap-2 font-semibold tracking-tight"
                >
                    <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                        <Hand className="size-4" />
                    </span>
                    {APP_NAME}
                </Link>

                <nav className="flex items-center gap-1 sm:gap-2">
                    <LanguageSwitcher />

                    {status === "loading" && <Skeleton className="size-9 rounded-full" />}

                    {status === "authenticated" && user && <UserMenu user={user} />}

                    {status === "unauthenticated" && (
                        <>
                            <Button asChild variant="ghost" size="sm">
                                <Link href={AppRoute.LOGIN}>{t("nav.login")}</Link>
                            </Button>
                            <Button asChild size="sm">
                                <Link href={AppRoute.REGISTER}>{t("nav.register")}</Link>
                            </Button>
                        </>
                    )}
                </nav>
            </div>
        </header>
    );
}
