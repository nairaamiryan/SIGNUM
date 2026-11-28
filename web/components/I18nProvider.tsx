"use client";

import { useEffect } from "react";
import { I18nextProvider } from "react-i18next";
import i18n from "@/lib/i18n";
import { readStoredLanguage } from "@/lib/language";

export default function I18nProvider({ children }: { children: React.ReactNode }) {
    // The server and the first client render use the default language, so the
    // language chosen earlier by the user is applied after hydration.
    useEffect(() => {
        const stored = readStoredLanguage();
        if (stored && stored !== i18n.language) {
            void i18n.changeLanguage(stored);
        }
    }, []);

    return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
