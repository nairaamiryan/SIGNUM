import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import Header from "@/components/Header";
import I18nProvider from "@/components/I18nProvider";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
    variable: "--font-geist-sans",
    subsets: ["latin"],
});

const geistMono = Geist_Mono({
    variable: "--font-geist-mono",
    subsets: ["latin"],
});

export const metadata: Metadata = {
    title: "SIGNUM",
    description: "Armenian Sign Language recognition",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
    return (
        <html
            lang="hy"
            className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
        >
            <body className="flex min-h-full flex-col">
                <I18nProvider>
                    <AuthProvider>
                        <Header />
                        {children}
                        <Toaster />
                    </AuthProvider>
                </I18nProvider>
            </body>
        </html>
    );
}
