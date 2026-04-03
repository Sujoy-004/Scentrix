'use client';

import { HeroSection } from '@/components/HeroSection';
import { HowItWorks } from '@/components/HowItWorks';
import { FragranceFamilies } from '@/components/FragranceFamilies';
import { SocialProof } from '@/components/SocialProof';
import { FinalCTA } from '@/components/FinalCTA';
import { ScrollSequence } from '@/components/ScrollSequence';

export default function Home() {
  return (
    <>
      <ScrollSequence 
        frameCount={240} 
        basePath="/assets/all_extracted"
        isFixed={true}
      />

      <HeroSection />

      <HowItWorks />
      
      <FragranceFamilies />
      <SocialProof />
      <FinalCTA />
    </>
  );
}
