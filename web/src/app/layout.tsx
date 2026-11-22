import type { Metadata } from "next";
import { Outfit, Source_Sans_3 } from "next/font/google";

import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  weight: ["500", "600", "700", "800"],
});

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source-sans",
  weight: ["400", "500", "600", "700"],
});

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
      <body
        className={`${outfit.variable} ${sourceSans.variable} bg-canvas font-body text-ink antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
