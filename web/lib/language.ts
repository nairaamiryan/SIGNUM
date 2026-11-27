import { DEFAULT_LANGUAGE, LANGUAGE_STORAGE_KEY, Language } from "./constants";

type LanguageCode = Language;

export const SUPPORTED_LANGUAGES: readonly LanguageCode[] = [Language.HY_AM, Language.HY_WM];

export function isSupportedLanguage(value: unknown): value is LanguageCode {
    return SUPPORTED_LANGUAGES.some((language) => language === value);
}

export function readStoredLanguage(): LanguageCode | null {
    try {
        const value = localStorage.getItem(LANGUAGE_STORAGE_KEY);
        return isSupportedLanguage(value) ? value : null;
    } catch {
        return null;
    }
}

export function storeLanguage(language: LanguageCode): void {
    try {
        localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
        // Storage can be unavailable; the choice then lasts until the page is reloaded.
    }
}

export function normalizeLanguage(value: string | undefined): LanguageCode {
    return isSupportedLanguage(value) ? value : DEFAULT_LANGUAGE;
}
