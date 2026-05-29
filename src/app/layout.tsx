import type { Metadata } from "next";
import { Inter, Merriweather } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const merriweather = Merriweather({
  variable: "--font-merriweather",
  weight: ["300", "400", "700", "900"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Vachan Study | Immersive Scripture Study & AI Assistant",
  description: "Explore, study, and understand the Bible with Vachan Study Bible Study Chatbot. Sync Scripture with AI answers using the unfoldingWord dataset in a high-fidelity workspace.",
  keywords: ["Bible study", "Vachan Study Chatbot", "Scripture analysis", "unfoldingWord", "Christian Theology", "Matthew 1 study"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${merriweather.variable} h-full scroll-smooth`}
    >
      <body className="min-h-full font-sans antialiased bg-stone-50 text-stone-900 dark:bg-zinc-950 dark:text-zinc-100 selection:bg-amber-500/30">
        {children}
      </body>
    </html>
  );
}
