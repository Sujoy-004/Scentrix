'use client';

import { HeroSection } from '@/components/HeroSection';
import { HowItWorks } from '@/components/HowItWorks';
import { FragranceFamilies } from '@/components/FragranceFamilies';
import { SocialProof } from '@/components/SocialProof';
import { FinalCTA } from '@/components/FinalCTA';
import { VideoScrubber } from '@/components/VideoScrubber';
import { ScrollShowcase } from '@/components/ScrollShowcase';

export default function Home() {
  return (
    <>
      <VideoScrubber
        videoPath="/assets/top_hero.mp4"
        isFixed={true}
      />

      <HeroSection />

      <ScrollShowcase />

      <HowItWorks />
      
      <FragranceFamilies />
      <SocialProof />
      <FinalCTA />
    </>
  );
}
