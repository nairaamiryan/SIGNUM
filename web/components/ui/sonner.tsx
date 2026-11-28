"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

/** App-wide toast host. Notifications are created with `toast.success(...)` from "sonner". */
function Toaster(props: ToasterProps) {
    return (
        <Sonner
            theme="system"
            position="top-center"
            className="toaster group"
            style={
                {
                    "--normal-bg": "var(--popover)",
                    "--normal-text": "var(--popover-foreground)",
                    "--normal-border": "var(--border)",
                } as React.CSSProperties
            }
            {...props}
        />
    );
}

export { Toaster };
