"use client";

import { forwardRef, useState, type ComponentProps } from "react";
import { Eye, EyeOff } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type PasswordInputProps = Omit<ComponentProps<typeof Input>, "type">;

/** Password field with a button that shows or hides the typed text. */
const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
    function PasswordInput(props, ref) {
        const { t } = useTranslation();
        const [visible, setVisible] = useState(false);

        return (
            <div className="relative">
                <Input
                    ref={ref}
                    type={visible ? "text" : "password"}
                    className="pr-11"
                    {...props}
                />
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute top-0 right-0 size-10 text-muted-foreground"
                    onClick={() => setVisible((value) => !value)}
                    aria-label={
                        visible ? t("auth.fields.hidePassword") : t("auth.fields.showPassword")
                    }
                >
                    {visible ? <EyeOff /> : <Eye />}
                </Button>
            </div>
        );
    },
);

export default PasswordInput;
