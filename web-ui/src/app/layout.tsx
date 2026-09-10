import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SiteSync AI",
  description: "Intelligent Data Capture & Schedule-Linking Layer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-900 text-slate-50 min-h-screen flex flex-col">
        <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🏗️</span>
              <h1 className="text-xl font-bold tracking-tight text-white">
                SiteSync <span className="text-cyan-400">AI</span>
              </h1>
            </div>
            <nav className="flex gap-6">
              <a href="/" className="text-sm font-medium hover:text-cyan-400 transition-colors">Time Agent</a>
              <a href="/queue" className="text-sm font-medium hover:text-cyan-400 transition-colors">Review Queue</a>
              <a href="/memory" className="text-sm font-medium hover:text-cyan-400 transition-colors">Memory</a>
            </nav>
          </div>
        </header>
        <main className="flex-1 w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </body>
    </html>
  );
}
