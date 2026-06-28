import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

const manrope = Manrope({
  subsets: ["latin", "cyrillic"],
  variable: "--font-manrope",
  display: "swap",
});

export const metadata: Metadata = {
  title: "MedServicePrice.kz — сравнение цен на медуслуги",
  description:
    "Агрегатор цен на анализы, приёмы врачей и диагностику в клиниках Казахстана.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={`${inter.variable} ${manrope.variable}`}>
      <body className="min-h-screen bg-page font-sans text-ink antialiased">
        <header className="sticky top-0 z-30 border-b border-line/70 bg-surface/80 backdrop-blur">
          <div className="mx-auto flex max-w-content items-center justify-between px-6 py-3.5">
            <Link
              href="/"
              className="flex items-center gap-2.5 font-display text-lg font-bold text-navy"
            >
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-hero-teal text-base font-bold text-white shadow-soft">
                М
              </span>
              MedServicePrice
              <span className="font-normal text-ink-muted">.kz</span>
            </Link>
            <nav className="flex items-center gap-1 text-sm font-medium text-ink-secondary">
              <Link
                href="/"
                className="rounded-lg px-3 py-2 transition hover:bg-subtle hover:text-navy"
              >
                Поиск
              </Link>
              <Link
                href="/admin"
                className="rounded-lg px-3 py-2 transition hover:bg-subtle hover:text-navy"
              >
                Админка
              </Link>
            </nav>
          </div>
        </header>

        <main className="mx-auto max-w-content px-6 py-8">{children}</main>

        <footer className="mx-auto max-w-content px-6 pb-10 pt-4">
          <div className="border-t border-line pt-6 text-xs leading-relaxed text-ink-muted">
            Данные собираются из открытых источников. Цены носят справочный
            характер — уточняйте в клинике. Дата обновления указана у каждой цены.
          </div>
        </footer>
      </body>
    </html>
  );
}
