import { themeCSS } from "./theme";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import ChromeBoundary from "./components/ChromeBoundary";

export const metadata: Metadata = {
  title: "Юридична AI-Платформа",
  description: "Автоматизуй юридичну роботу за допомогою штучного інтелекту",
  keywords: "юридичні документи, AI, автоматизація, судові документи, Україна",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="uk">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
        <style dangerouslySetInnerHTML={{ __html: themeCSS }} />
        <style dangerouslySetInnerHTML={{ __html: `.inter-font { font-family: 'Inter', sans-serif; }` }} />
      </head>
      <body className="inter-font">
        <ChromeBoundary>{children}</ChromeBoundary>
      </body>
    </html>
  );
}
