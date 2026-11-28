import type { ReactNode } from "react";
import { Label } from "@/components/ui/label";

interface FormFieldProps {
    id: string;
    label: string;
    /** Already translated message, shown under the field. */
    error?: string;
    children: ReactNode;
}

/** Label, input and validation message of one form field. */
export default function FormField({ id, label, error, children }: FormFieldProps) {
    return (
        <div className="flex flex-col gap-2">
            <Label htmlFor={id}>{label}</Label>
            {children}
            {error && (
                <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
                    {error}
                </p>
            )}
        </div>
    );
}
