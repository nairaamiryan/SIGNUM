import type { ReactNode } from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

interface AuthShellProps {
    title: string;
    description: string;
    footer: ReactNode;
    children: ReactNode;
}

/** Centered card that frames the login and registration forms. */
export default function AuthShell({ title, description, footer, children }: AuthShellProps) {
    return (
        <main className="flex flex-1 items-center justify-center px-4 py-10">
            <Card className="w-full max-w-md">
                <CardHeader>
                    <CardTitle className="text-2xl">{title}</CardTitle>
                    <CardDescription>{description}</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-5">{children}</CardContent>
                <CardFooter className="justify-center text-sm text-muted-foreground">
                    {footer}
                </CardFooter>
            </Card>
        </main>
    );
}
