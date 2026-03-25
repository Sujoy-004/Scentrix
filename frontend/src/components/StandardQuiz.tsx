'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import { getQuizFragrances } from '@/lib/mockData';
import '@/app/onboarding/quiz/quiz.css';

export default function StandardQuiz() {
  const router = useRouter();
  const [currentFragranceIndex, setCurrentFragranceIndex] = useState(0);
  const [rating, setRating] = useState<number | null>(null);

  const { addQuizResponse } = useAppStore();
  
  // Load fragrances from mock data (no API calls needed)
  const fragrances = getQuizFragrances();
  const isLoading = false;

  const handleRating = (value: number) => {
    setRating(value);
  };

  const handleNext = () => {
    if (rating === null || !fragrances) return;

    const currentFragrance = fragrances[currentFragranceIndex];
    addQuizResponse({
      fragrance_id: currentFragrance.id,
      rating,
    });

    if (currentFragranceIndex < fragrances.length - 1) {
      setCurrentFragranceIndex(currentFragranceIndex + 1);
      setRating(null);
    } else {
      // Quiz complete - go to recommendations
      router.push('/recommendations');
    }
  };

  const handleSkip = () => {
    if (currentFragranceIndex < fragrances.length - 1) {
      setCurrentFragranceIndex(currentFragranceIndex + 1);
      setRating(null);
    } else {
      // Quiz complete - go to recommendations
      router.push('/recommendations');
    }
  };

  if (isLoading || !fragrances || fragrances.length === 0) {
    return <div className="quiz-loading">Loading fragrances...</div>;
  }

  const currentFragrance = fragrances[currentFragranceIndex];
  const progress = ((currentFragranceIndex + 1) / fragrances.length) * 100;

  return (
    <div className="quiz-page">
      <div className="quiz-container">
        <div className="quiz-header">
          <h1>Discover Your Signature Scent</h1>
          <p>Rate your favorite fragrances to get personalized recommendations</p>
        </div>

        <div className="quiz-progress-bar" style={{ width: `${progress}%` }}></div>

        <div className="quiz-card">
          <div className="fragrance-preview">
            <div className="fragrance-emoji">🧴</div>
            <h2 className="fragrance-title">{currentFragrance.name}</h2>
            <p className="fragrance-brand">{currentFragrance.brand}</p>
          </div>

          <div className="rating-section">
            <p className="rating-label">How much do you like this fragrance?</p>
            <div className="rating-slider">
              <input
                type="range"
                min="1"
                max="10"
                value={rating || 5}
                onChange={(e) => handleRating(Number(e.target.value))}
                className="slider"
              />
              <div className="rating-display">{rating || 5} / 10</div>
            </div>

            <div className="rating-labels">
              <span className="left">Not My Style</span>
              <span className="right">Perfect Match!</span>
            </div>
          </div>

          <div className="quiz-notes-preview">
            <p className="notes-title">Top Notes:</p>
            <div className="notes-pills">
              {currentFragrance.top_notes?.map((note: string) => (
                <span key={note} className="note-pill">
                  {note}
                </span>
              ))}
            </div>
          </div>

          <div className="quiz-controls">
            <button
              className="quiz-btn quiz-btn-skip"
              onClick={handleSkip}
            >
              Skip
            </button>
            <button
              className="quiz-btn quiz-btn-next-primary"
              onClick={handleNext}
              disabled={rating === null}
            >
              {currentFragranceIndex === fragrances.length - 1 ? 'Get Recommendations' : 'Next Fragrance'}
            </button>
          </div>

          <div className="quiz-counter">
            {currentFragranceIndex + 1} of {fragrances.length}
          </div>
        </div>
      </div>
    </div>
  );
}
