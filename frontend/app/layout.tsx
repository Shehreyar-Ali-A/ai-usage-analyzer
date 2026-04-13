import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "AI Workspace Platform",
  description: "Assignment-based AI workspace for students",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <a href="/workspaces" className="text-xl font-bold text-indigo-600">
              AI Workspace
            </a>
            <nav className="flex items-center gap-6 text-sm text-gray-600">
              <a href="/workspaces" className="hover:text-gray-900">
                My Workspaces
              </a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
