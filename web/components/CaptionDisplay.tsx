"use client";

import { useTranslation } from "react-i18next";
import type { CaptionEntry, PartialGloss } from "@/lib/captionFeed";
import { SentenceStatus, UNCERTAIN_CONFIDENCE } from "@/lib/constants";
import type { SentenceStatus as SentenceStatusType } from "@/lib/types";

interface CaptionDisplayProps {
    /** Signs recognized so far in the utterance that is still in progress. */
    partials: PartialGloss[];
    /** Completed captions, newest first. */
    captions: CaptionEntry[];
    /** A sentence is being generated for an utterance that has ended. */
    generating: boolean;
    unrecognized: boolean;
    error: string | null;
}

// Warnings of the NLP layer that are explained to the user. Technical ones
// (llm_timeout, invalid_output, ...) only produce the "fallback" status.
const KNOWN_WARNINGS = [
    "missing_glosses",
    "uncertain_glosses",
    "omitted_glosses",
    "incomplete",
] as const;

const STATUS_BADGE_CLASS: Record<SentenceStatusType, string> = {
    [SentenceStatus.OK]:
        "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    [SentenceStatus.PARTIAL]:
        "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    [SentenceStatus.FALLBACK]: "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

const CARD_BORDER_CLASS: Record<SentenceStatusType, string> = {
    [SentenceStatus.OK]: "border-emerald-300 dark:border-emerald-800",
    [SentenceStatus.PARTIAL]: "border-amber-300 dark:border-amber-800",
    [SentenceStatus.FALLBACK]: "border-zinc-300 dark:border-zinc-700",
};

function percent(confidence: number): string {
    return `${(confidence * 100).toFixed(0)}%`;
}

export default function CaptionDisplay({
    partials,
    captions,
    generating,
    unrecognized,
    error,
}: CaptionDisplayProps) {
    const { t } = useTranslation();

    const [latest, ...earlier] = captions;
    const showPlaceholder =
        partials.length === 0 && !generating && !unrecognized && !error && !latest;

    return (
        <div className="w-full max-w-2xl flex flex-col gap-3">
            {error && (
                <div
                    role="alert"
                    className="rounded-lg border border-red-300 dark:border-red-900 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-700 dark:text-red-300"
                >
                    <span className="font-semibold">⛔ {t("state.error")}:</span> {error}
                </div>
            )}

            {unrecognized && (
                <p
                    role="status"
                    className="rounded-lg border border-amber-300 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/40 px-4 py-3 text-sm font-medium text-amber-700 dark:text-amber-300"
                >
                    ⚠ {t("caption.unrecognized")}
                </p>
            )}

            {/* Live area: partial results of the utterance in progress. */}
            {(partials.length > 0 || generating) && (
                <div
                    aria-live="polite"
                    className="rounded-lg border border-dashed border-zinc-300 dark:border-zinc-700 px-4 py-3"
                >
                    {partials.length > 0 && (
                        <>
                            <p className="text-xs text-zinc-500 mb-2">{t("caption.partial")}</p>
                            <ul className="flex flex-wrap gap-2">
                                {partials.map((partial) => {
                                    const uncertain = partial.confidence < UNCERTAIN_CONFIDENCE;
                                    return (
                                        <li
                                            key={partial.id}
                                            className={`rounded-full px-3 py-1 text-sm border ${
                                                uncertain
                                                    ? "border-amber-300 text-amber-700 dark:border-amber-800 dark:text-amber-300"
                                                    : "border-zinc-300 text-zinc-800 dark:border-zinc-600 dark:text-zinc-100"
                                            }`}
                                            title={
                                                uncertain
                                                    ? t("caption.uncertain")
                                                    : t("caption.confidence", {
                                                          value: (partial.confidence * 100).toFixed(
                                                              0,
                                                          ),
                                                      })
                                            }
                                        >
                                            {partial.gloss}
                                            <span className="ml-2 text-xs text-zinc-500">
                                                {percent(partial.confidence)}
                                            </span>
                                        </li>
                                    );
                                })}
                            </ul>
                        </>
                    )}
                    {generating && (
                        <p className="text-sm text-zinc-500 animate-pulse mt-1">
                            {t("caption.generating")}
                        </p>
                    )}
                </div>
            )}

            {showPlaceholder && (
                <div className="min-h-[72px] rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 px-4 py-3 flex items-center">
                    <p className="text-zinc-400 text-sm">{t("caption.placeholder")}</p>
                </div>
            )}

            {/* Completed caption: the final sentence. */}
            {latest && (
                <div
                    className={`rounded-lg border-2 bg-zinc-50 dark:bg-zinc-900 px-4 py-3 ${CARD_BORDER_CLASS[latest.status]}`}
                >
                    <div className="flex items-center gap-2 mb-2">
                        <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASS[latest.status]}`}
                        >
                            {t(`caption.status.${latest.status}`)}
                        </span>
                        {latest.confidence !== null && (
                            <span className="text-xs text-zinc-500">
                                {t("caption.confidence", {
                                    value: (latest.confidence * 100).toFixed(0),
                                })}
                            </span>
                        )}
                    </div>

                    <p
                        className={`text-lg ${
                            latest.status === SentenceStatus.FALLBACK
                                ? "text-zinc-600 dark:text-zinc-300"
                                : "text-zinc-900 dark:text-zinc-50"
                        }`}
                    >
                        {latest.text}
                    </p>

                    {latest.status === SentenceStatus.FALLBACK && (
                        <p className="text-xs text-zinc-500 mt-1">{t("caption.fallbackHint")}</p>
                    )}

                    {latest.glosses.length > 0 && latest.status !== SentenceStatus.FALLBACK && (
                        <p className="text-xs text-zinc-500 mt-1">
                            {t("caption.gloss")}: {latest.glosses.join(" → ")}
                        </p>
                    )}

                    {KNOWN_WARNINGS.filter((w) => latest.warnings.includes(w)).map((warning) => (
                        <p
                            key={warning}
                            className="text-xs text-amber-700 dark:text-amber-400 mt-1"
                        >
                            ⚠ {t(`caption.warnings.${warning}`)}
                        </p>
                    ))}
                </div>
            )}

            {earlier.length > 0 && (
                <div>
                    <p className="text-xs text-zinc-500 mb-1">{t("caption.history")}</p>
                    <ul className="flex flex-col gap-1">
                        {earlier.map((caption) => (
                            <li
                                key={caption.id}
                                className="text-sm text-zinc-600 dark:text-zinc-400 flex items-center gap-2"
                            >
                                <span
                                    className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_BADGE_CLASS[caption.status]}`}
                                >
                                    {t(`caption.status.${caption.status}`)}
                                </span>
                                <span>{caption.text}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
