"use client";

import { useTranslation } from "react-i18next";

interface CaptionDisplayProps {
    caption: string;
    gloss: string[];
    confidence: number | null;
    unrecognized: boolean;
}

export default function CaptionDisplay({
    caption,
    gloss,
    confidence,
    unrecognized,
}: CaptionDisplayProps) {
    const { t } = useTranslation();

    return (
        <div className="w-full max-w-2xl min-h-[72px] rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 px-4 py-3 flex flex-col justify-center">
            {unrecognized ? (
                <p className="text-amber-600 dark:text-amber-400 text-sm font-medium flex items-center gap-2">
                    ⚠ {t("caption.unrecognized")}
                </p>
            ) : caption ? (
                <>
                    <p className="text-lg text-zinc-900 dark:text-zinc-50">{caption}</p>
                    {gloss.length > 0 && (
                        <p className="text-xs text-zinc-500 mt-1">
                            {t("caption.gloss")}: {gloss.join(" → ")}
                        </p>
                    )}
                    {confidence !== null && (
                        <p className="text-xs text-zinc-500 mt-1">
                            {t("caption.confidence", { value: (confidence * 100).toFixed(0) })}
                        </p>
                    )}
                </>
            ) : (
                <p className="text-zinc-400 text-sm">{t("caption.placeholder")}</p>
            )}
        </div>
    );
}