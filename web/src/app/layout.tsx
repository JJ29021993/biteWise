import type { Metadata } from "next";

import "@fontsource/outfit/500.css";
import "@fontsource/outfit/600.css";
import "@fontsource/outfit/700.css";
import "@fontsource/outfit/800.css";
import "@fontsource/source-sans-3/400.css";
import "@fontsource/source-sans-3/500.css";
import "@fontsource/source-sans-3/600.css";
import "@fontsource/source-sans-3/700.css";

import "./globals.css";

export const metadata: Metadata = {
  title: "BiteWise · Discover restaurants",
  description:
    "AI-curated Bangalore restaurant recommendations with grounded Zomato facts.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-canvas font-body text-ink antialiased">{children}</body>
    </html>
  );
}
