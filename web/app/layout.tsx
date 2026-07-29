import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import "./globals.css";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: "Longform — faceless long-form video engine",
  description:
    "Plan and write faceless 8 to 30 minute YouTube videos: a retention-engineered chapter outline, narration written one chapter at a time, and a shot list per section.",
  openGraph: {
    title: "Longform",
    description:
      "Plan and write faceless long-form YouTube videos. Chapter outline, per-chapter narration, shot list.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
