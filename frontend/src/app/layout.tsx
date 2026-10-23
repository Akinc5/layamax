import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LayaPulse — Real-Time X Intelligence",
  description:
    "Understand the live conversation. AI-powered real-time social media intelligence dashboard with Laya classification, RAG, and trend detection.",
  keywords: [
    "AI", "Twitter", "X", "social media", "intelligence",
    "analytics", "real-time", "RAG", "NLP", "dashboard",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>" />
      </head>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
