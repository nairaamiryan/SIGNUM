"use client";

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import hyAM from "../public/locales/hy-AM/common.json";
import hyWM from "../public/locales/hy-WM/common.json";
import { DEFAULT_LANGUAGE, Language } from "./constants";

i18n.use(initReactI18next).init({
    resources: {
        [Language.HY_AM]: { translation: hyAM },
        [Language.HY_WM]: { translation: hyWM },
    },
    lng: DEFAULT_LANGUAGE,
    fallbackLng: DEFAULT_LANGUAGE,
    // The resources are bundled, so initialization can finish synchronously and
    // the first render already has its translations.
    initAsync: false,
    interpolation: {
        escapeValue: false,
    },
});

export default i18n;
