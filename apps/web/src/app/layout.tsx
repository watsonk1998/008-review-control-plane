import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./theme.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "008 Review Control Plane",
  description: "Formal Review Control Plane and Execution Engine",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" className={`${inter.variable}`}>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
