'use client';

import { HeroSection } from '@/components/HeroSection';
import { ClickSprayEffect } from '@/components/ClickSprayEffect';
import { HowItWorks } from '@/components/HowItWorks';
import { FragranceFamilies } from '@/components/FragranceFamilies';
import { SocialProof } from '@/components/SocialProof';
import { ProductGrid } from '@/components/ProductGrid';
import { FinalCTA } from '@/components/FinalCTA';

export default function Home() {
  return (
    <>
      <ClickSprayEffect />
      <HeroSection />
      <HowItWorks />
      <FragranceFamilies />
      <SocialProof />
      <ProductGrid />
      <FinalCTA />
    </>
  );
}
