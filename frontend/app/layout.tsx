import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "AI Usage Analyzer",
  description: "Analyze AI reliance in student assignments"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

