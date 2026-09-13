'use client';

import { useEffect, useState } from 'react';
import { DiscoveryNeuralLoader } from '@/components/DiscoveryNeuralLoader';
import StandardQuiz from '@/components/StandardQuiz';
import './quiz.css';

export default function QuizPage() {
  const [isMounted, setIsMounted] = useState(false);

  // Forced Neural Sync: Triggering Next.js route re-registration
  useEffect(() => {
    setIsMounted(true);
    console.log('Scentrix Personality Engine: Neural Link Established.');
  }, []);

  if (!isMounted) {
    return <DiscoveryNeuralLoader title="Initializing Neural Core..." />;
  }

  return <StandardQuiz />;
}
