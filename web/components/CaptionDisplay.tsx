"use client";

import { TriangleAlert, OctagonAlert } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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

const STATUS_BADGE_VARIANT: Record<SentenceStatusType, "success" | "warning" | "secondary"> = {
    [SentenceStatus.OK]: "success",
    [SentenceStatus.PARTIAL]: "warning",
    [SentenceStatus.FALLBACK]: "secondary",
};

const CARD_BORDER_CLASS: Record<SentenceStatusType, string> = {
    [SentenceStatus.OK]: "border-success/60",
    [SentenceStatus.PARTIAL]: "border-warning/70",
    [SentenceStatus.FALLBACK]: "border-border",
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
        <div className="flex w-full flex-col gap-3">
            {error && (
                <Alert variant="destructive">
                    <OctagonAlert />
                    <AlertDescription>
                        <span>
                            <span className="font-semibold">{t("state.error")}:</span> {error}
                        </span>
                    </AlertDescription>
                </Alert>
            )}

            {unrecognized && (
                <Alert variant="warning" role="status">
                    <TriangleAlert />
                    <AlertDescription>{t("caption.unrecognized")}</AlertDescription>
                </Alert>
            )}

            {/* Live area: partial results of the utterance in progress. */}
            {(partials.length > 0 || generating) && (
                <div aria-live="polite" className="rounded-lg border border-dashed px-4 py-3">
                    {partials.length > 0 && (
                        <>
                            <p className="mb-2 text-xs text-muted-foreground">
                                {t("caption.partial")}
                            </p>
                            <ul className="flex flex-wrap gap-2">
                                {partials.map((partial) => {
                                    const uncertain = partial.confidence < UNCERTAIN_CONFIDENCE;
                                    return (
                                        <li
                                            key={partial.id}
                                            className={`rounded-full border px-3 py-1 text-sm ${
                                                uncertain
                                                    ? "border-warning/70 text-warning-foreground dark:text-warning"
                                                    : "text-foreground"
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
                                            <span className="ml-2 text-xs text-muted-foreground">
                                                {percent(partial.confidence)}
                                            </span>
                                        </li>
                                    );
                                })}
                            </ul>
                        </>
                    )}
                    {generating && (
                        <p className="mt-1 animate-pulse text-sm text-muted-foreground">
                            {t("caption.generating")}
                        </p>
                    )}
                </div>
            )}

            {showPlaceholder && (
                <div className="flex min-h-[72px] items-center rounded-lg border bg-muted/40 px-4 py-3">
                    <p className="text-sm text-muted-foreground">{t("caption.placeholder")}</p>
                </div>
            )}

            {/* Completed caption: the final sentence. */}
            {latest && (
                <div
                    className={`rounded-lg border-2 bg-muted/40 px-4 py-3 ${CARD_BORDER_CLASS[latest.status]}`}
                >
                    <div className="mb-2 flex items-center gap-2">
                        <Badge variant={STATUS_BADGE_VARIANT[latest.status]}>
                            {t(`caption.status.${latest.status}`)}
                        </Badge>
                        {latest.confidence !== null && (
                            <span className="text-xs text-muted-foreground">
                                {t("caption.confidence", {
                                    value: (latest.confidence * 100).toFixed(0),
                                })}
                            </span>
                        )}
                    </div>

                    <p
                        className={`text-lg ${
                            latest.status === SentenceStatus.FALLBACK
                                ? "text-muted-foreground"
                                : "text-foreground"
                        }`}
                    >
                        {latest.text}
                    </p>

                    {latest.status === SentenceStatus.FALLBACK && (
                        <p className="mt-1 text-xs text-muted-foreground">
                            {t("caption.fallbackHint")}
                        </p>
                    )}

                    {latest.glosses.length > 0 && latest.status !== SentenceStatus.FALLBACK && (
                        <p className="mt-1 text-xs text-muted-foreground">
                            {t("caption.gloss")}: {latest.glosses.join(" → ")}
                        </p>
                    )}

                    {KNOWN_WARNINGS.filter((w) => latest.warnings.includes(w)).map((warning) => (
                        <p
                            key={warning}
                            className="mt-1 text-xs text-warning-foreground dark:text-warning"
                        >
                            ⚠ {t(`caption.warnings.${warning}`)}
                        </p>
                    ))}
                </div>
            )}

            {earlier.length > 0 && (
                <div>
                    <p className="mb-1 text-xs text-muted-foreground">{t("caption.history")}</p>
                    <ul className="flex flex-col gap-1">
                        {earlier.map((caption) => (
                            <li
                                key={caption.id}
                                className="flex items-center gap-2 text-sm text-muted-foreground"
                            >
                                <Badge
                                    variant={STATUS_BADGE_VARIANT[caption.status]}
                                    className="px-2 py-0 text-[10px]"
                                >
                                    {t(`caption.status.${caption.status}`)}
                                </Badge>
                                <span>{caption.text}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
