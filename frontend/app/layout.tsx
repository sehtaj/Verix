import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Verix",
  description: "Generate evidence, investigate failures, and verify Python repositories safely.",
};

export const viewport: Viewport = {
  themeColor: "#131313",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
