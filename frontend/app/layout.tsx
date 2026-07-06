import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "EquityLens",
  description:
    "AI investment research platform — SEC filings, fundamentals and cited answers.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-screen bg-slate-50 font-sans text-slate-900 antialiased">
        <header className="border-b border-slate-200 bg-slate-900 text-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              Equity<span className="text-emerald-400">Lens</span>
            </Link>
            <nav className="flex gap-6 text-sm text-slate-300">
              <Link href="/" className="hover:text-white">
                Screener
              </Link>
              <Link href="/about" className="hover:text-white">
                About
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 pb-8 text-xs text-slate-400">
          Educational project — not investment advice. Data: SEC EDGAR, Yahoo
          Finance.
        </footer>
      </body>
    </html>
  );
}
