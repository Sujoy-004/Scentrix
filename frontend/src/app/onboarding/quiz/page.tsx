'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import FlashcardQuiz from '@/components/FlashcardQuiz';
import StandardQuiz from '@/components/StandardQuiz';
import './quiz.css';

export default function QuizPage() {
  const { isAuthenticated } = useAppStore();
  const [isMounted, setIsMounted] = useState(false);

  // Prevent hydration mismatch
  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return <div className="quiz-loading">Loading...</div>;
  }

  // Show flashcard format for authenticated users, standard for others
  if (isAuthenticated) {
    return <FlashcardQuiz />;
  }

  return <StandardQuiz />;
}
