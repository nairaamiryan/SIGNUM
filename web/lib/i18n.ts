"use client";

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import hyAM from "../public/locales/hy-AM/common.json";
import hyWM from "../public/locales/hy-WM/common.json";

i18n.use(initReactI18next).init({
    resources: {
        "hy-AM": { translation: hyAM },
        "hy-WM": { translation: hyWM },
    },
    lng: "hy-AM",
    fallbackLng: "hy-AM",
    interpolation: {
        escapeValue: false,
    },
});

export default i18n;