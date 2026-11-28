"use client";

import { Globe } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    isSupportedLanguage,
    normalizeLanguage,
    storeLanguage,
    SUPPORTED_LANGUAGES,
} from "@/lib/language";

export default function LanguageSwitcher() {
    const { t, i18n } = useTranslation();
    const current = normalizeLanguage(i18n.language);

    const handleChange = (value: string) => {
        if (!isSupportedLanguage(value)) return;
        storeLanguage(value);
        void i18n.changeLanguage(value);
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" aria-label={t("nav.language")}>
                    <Globe />
                    <span className="hidden sm:inline">{t(`language.${current}`)}</span>
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuRadioGroup value={current} onValueChange={handleChange}>
                    {SUPPORTED_LANGUAGES.map((language) => (
                        <DropdownMenuRadioItem key={language} value={language}>
                            {t(`language.${language}`)}
                        </DropdownMenuRadioItem>
                    ))}
                </DropdownMenuRadioGroup>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
