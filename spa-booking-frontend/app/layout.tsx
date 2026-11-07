import type { Metadata } from "next";
import Link from "next/link";
import { Be_Vietnam_Pro, Bricolage_Grotesque } from "next/font/google";
import AuthNav from "@/components/AuthNav";
import ChatWidget from "@/components/chatbot/ChatWidget";
import Providers from "@/components/Providers";
import "./globals.css";

const body = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
});

const display = Bricolage_Grotesque({
  subsets: ["latin", "vietnamese"],
  weight: ["500", "700"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "AI Massage Booking",
  description: "Smart booking system for massage appointments",
};

function StoneMark() {
  return (
    <svg width="26" height="26" viewBox="0 0 28 28" aria-hidden="true">
      <ellipse cx="14" cy="19" rx="11" ry="6" fill="#3E7F72" />
      <ellipse cx="14" cy="13" rx="8" ry="4.5" fill="#6FB1A2" />
      <ellipse cx="14" cy="8" rx="5" ry="3" fill="#D9E9E4" />
    </svg>
  );
}

function NavBar() {
  return (
    <nav className="bg-basalt">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 font-display text-xl font-bold tracking-tight text-white">
            <StoneMark />
            Massage Booking App
          </Link>
          <AuthNav />
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${body.variable} ${display.variable} font-sans`}>
        <Providers>
          <NavBar />
          {children}
          <ChatWidget />
          <footer className="border-t border-line bg-linen">
            <div className="container mx-auto px-4 py-6 text-center text-sm text-ink-soft">
              <p>&copy; 2026 Massage Booking App. All rights reserved.</p>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
