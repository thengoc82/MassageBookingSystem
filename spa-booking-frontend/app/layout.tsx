import { AuthProvider } from "@/contexts/AuthContext";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import ChatWidget from "@/components/chatbot/ChatWidget";
import "./globals.css";
import NavBar from "@/components/NavBar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "AI Massage Booking",
  description: "Smart booking system for massage appointments",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans`}>
        <AuthProvider>
          <NavBar />
          {children}
          <ChatWidget />
        </AuthProvider>
        <footer className="border-t border-gray-200 bg-gray-50">
          <div className="container mx-auto px-4 py-8 text-center text-gray-600">
            <p>&copy; 2026 Massage Booking App. All rights reserved.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
