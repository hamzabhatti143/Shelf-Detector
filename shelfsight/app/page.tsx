import type { Metadata } from "next";
import { JsonLd } from "@/components/ui/JsonLd";
import { Navbar } from "@/components/sections/Navbar";
import { Hero } from "@/components/sections/Hero";
import { Features } from "@/components/sections/Features";
import { HowItWorks } from "@/components/sections/HowItWorks";
import { Faq } from "@/components/sections/Faq";
import { CtaBanner } from "@/components/sections/CtaBanner";
import { Footer } from "@/components/sections/Footer";
import { SITE } from "@/lib/config";
import { FAQ_ITEMS } from "@/lib/content";

export const metadata: Metadata = {
  title: { absolute: `${SITE.name} | ${SITE.tagline}` },
  description: SITE.description,
  alternates: { canonical: "/" },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      name: SITE.name,
      url: SITE.url,
      description: SITE.description,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
    },
    {
      "@type": "FAQPage",
      mainEntity: FAQ_ITEMS.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: { "@type": "Answer", text: item.answer },
      })),
    },
  ],
};

export default function HomePage() {
  return (
    <>
      <JsonLd data={jsonLd} />
      <Navbar />
      <main id="main">
        <Hero />
        <Features />
        <HowItWorks />
        <Faq />
        <CtaBanner />
      </main>
      <Footer />
    </>
  );
}