'use client';

import { HeroSection } from '@/components/HeroSection';
import { HowItWorks } from '@/components/HowItWorks';
import { FragranceFamilies } from '@/components/FragranceFamilies';
import { SocialProof } from '@/components/SocialProof';
import { FinalCTA } from '@/components/FinalCTA';
import { VideoScrubber } from '@/components/VideoScrubber';

export default function Home() {
  return (
    <>
      <VideoScrubber 
        videoPath="/assets/top_hero.mp4"
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
