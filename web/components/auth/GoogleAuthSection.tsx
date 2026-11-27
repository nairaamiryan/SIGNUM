"use client";

import { GoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { useAuth } from "@/components/AuthProvider";
import { authErrorKey } from "@/lib/authClient";

// Read at build time. Without a client ID the Google option is not shown.
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

interface GoogleAuthSectionProps {
    /** Called with the i18n key of the error message when Google sign-in fails. */
    onError: (messageKey: string) => void;
}

/** "or" divider and the "Sign in with Google" button. */
export default function GoogleAuthSection({ onError }: GoogleAuthSectionProps) {
    const { t } = useTranslation();
    const { loginWithGoogle } = useAuth();

    if (!GOOGLE_CLIENT_ID) return null;

    const handleCredential = async (credential: string | undefined) => {
        if (!credential) {
            onError("auth.errors.googleFailed");
            return;
        }
        try {
            const user = await loginWithGoogle(credential);
            toast.success(t("auth.welcomeBack", { name: user.name ?? user.email }));
        } catch (error) {
            onError(authErrorKey(error, "google"));
        }
    };

    return (
        <>
            <div className="flex items-center gap-3 text-xs text-muted-foreground uppercase">
                <span className="h-px flex-1 bg-border" />
                {t("auth.or")}
                <span className="h-px flex-1 bg-border" />
            </div>
            <div className="flex justify-center">
                <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID} locale="hy">
                    <GoogleLogin
                        onSuccess={(response) => void handleCredential(response.credential)}
                        onError={() => onError("auth.errors.googleFailed")}
                        text="continue_with"
                        shape="rectangular"
                        width={320}
                        theme="outline"
                    />
                </GoogleOAuthProvider>
            </div>
        </>
    );
}
