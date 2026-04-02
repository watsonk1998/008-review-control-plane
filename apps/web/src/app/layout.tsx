import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "008 Review Control Plane",
  description: "DeepResearchAgent orchestration layer with DeepTutor, GPT Researcher, FastGPT, and local LLM adapters.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
