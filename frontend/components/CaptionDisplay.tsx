"use client";

interface CaptionDisplayProps {
    caption: string;
    confidence: number | null;
    unrecognized: boolean;
}

export default function CaptionDisplay({
    caption,
    confidence,
    unrecognized,
}: CaptionDisplayProps) {
    return (
        <div className="w-full max-w-2xl min-h-[72px] rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 px-4 py-3 flex flex-col justify-center">
            {unrecognized ? (
                <p className="text-amber-600 dark:text-amber-400 text-sm font-medium flex items-center gap-2">
                    ⚠ Gesture not recognized — please repeat the sign.
                </p>
            ) : caption ? (
                <>
                    <p className="text-lg text-zinc-900 dark:text-zinc-50">{caption}</p>
                    {confidence !== null && (
                        <p className="text-xs text-zinc-500 mt-1">
                            Confidence: {(confidence * 100).toFixed(0)}%
                        </p>
                    )}
                </>
            ) : (
                <p className="text-zinc-400 text-sm">Recognized captions will appear here…</p>
            )}
        </div>
    );
}