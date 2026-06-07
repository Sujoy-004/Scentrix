import type { Metadata } from "next";
import { Cormorant_Garamond } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Providers from "@/components/Providers";
import StringTuneManager from "@/components/StringTuneManager";
import CookieBanner from "@/components/CookieBanner";
import PageTransition from "@/components/PageTransition";
import { ToastContainer } from "@/components/Toast";
// import PostHogPageView from "@/components/PostHogPageView";
import { Suspense } from "react";

const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  display: "swap",
});



export const metadata: Metadata = {
  title: "Scentrix — Discover Your Perfect Fragrance",
  description:
    "AI-powered fragrance discovery platform. Find your signature scent through personalized recommendations powered by graph neural networks and natural language understanding.",
  keywords: "fragrance, perfume, AI recommendations, scent discovery, personalized",
  authors: [{ name: "Scentrix" }],
  openGraph: {
    title: "Scentrix — Discover Your Perfect Fragrance",
    description: "AI-powered fragrance discovery. Find your signature scent.",
    type: "website",
  },
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${cormorant.variable}`}
    >
      <body className="antialiased">
        <StringTuneManager />
        <Providers>
{/* <Suspense fallback={null}>
            <PostHogPageView />
          </Suspense> */}
          <Navbar />
          <main className="flex-1" style={{ paddingTop: "64px" }}>
            <PageTransition>
              {children}
            </PageTransition>
          </main>
          <CookieBanner />
          <ToastContainer />
        </Providers>

      </body>
    </html>
  );
}
