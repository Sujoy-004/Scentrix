'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import { getQuizFragrances, Fragrance } from '@/lib/mockData';

const FlashcardQuiz: React.FC = () => {
  const router = useRouter();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [rating, setRating] = useState(0);
  const { addQuizResponse, recommendations, setRecommendations } = useAppStore();
  
  const fragrances = getQuizFragrances();
  const currentFragrance = fragrances[currentIndex];

  if (!currentFragrance) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#4a7c59] to-[#2d5a3d] flex items-center justify-center">
        <div className="text-white text-center">
          <h2 className="text-3xl font-bold mb-4">Quiz Complete! 🎉</h2>
          <p className="text-lg mb-6">Your personalized recommendations are ready.</p>
          <button
            onClick={() => router.push('/recommendations')}
            className="bg-[#d4a574] text-white px-8 py-3 rounded-lg font-semibold hover:bg-[#c9935f] transition"
          >
            View My Recommendations
          </button>
        </div>
      </div>
    );
  }

  const handleRating = (value: number) => {
    setRating(value);
    addQuizResponse({
      fragrance_id: currentFragrance.id,
      rating: value,
      notes: `Family: ${currentFragrance.accords?.join(', ')}`,
    });

    // Auto advance after 500ms
    setTimeout(() => {
      setIsFlipped(false);
      setRating(0);
      setCurrentIndex(currentIndex + 1);
    }, 500);
  };

  const progressPercent = ((currentIndex) / fragrances.length) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#4a7c59] to-[#2d5a3d] flex flex-col items-center justify-center p-4">
      {/* Progress Bar */}
      <div className="w-full mb-8">
        <div className="h-2 bg-white/20 rounded-full overflow-hidden max-w-md">
          <div
            className="h-full bg-[#d4a574] transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="text-white text-sm mt-2 text-center">
          {currentIndex + 1} of {fragrances.length}
        </p>
      </div>

      {/* Flashcard */}
      <div
        className="w-full max-w-md h-96 cursor-pointer perspective"
        onClick={() => setIsFlipped(!isFlipped)}
        style={{
          perspective: '1000px',
        }}
      >
        <div
          className="relative w-full h-full transition-transform duration-500"
          style={{
            transformStyle: 'preserve-3d',
            transform: isFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
          }}
        >
          {/* Front of Card */}
          <div
            className="absolute w-full h-full bg-white rounded-2xl shadow-2xl p-8 flex flex-col items-center justify-center"
            style={{ backfaceVisibility: 'hidden' }}
          >
            <div className="text-center">
              <h3 className="text-3xl font-bold text-[#2d5a3d] mb-2">
                {currentFragrance.brand}
              </h3>
              <h2 className="text-4xl font-bold text-[#4a7c59] mb-4">
                {currentFragrance.name}
              </h2>
              <p className="text-gray-600 mb-4">{currentFragrance.concentration}</p>
              <div className="flex gap-2 flex-wrap justify-center mb-6">
                {currentFragrance.accords?.map((accord) => (
                  <span
                    key={accord}
                    className="px-3 py-1 bg-[#4a7c59] text-white rounded-full text-sm"
                  >
                    {accord}
                  </span>
                ))}
              </div>
              <p className="text-gray-500 text-sm">Click to see more</p>
            </div>
          </div>

          {/* Back of Card */}
          <div
            className="absolute w-full h-full bg-[#d4a574] rounded-2xl shadow-2xl p-8 flex flex-col items-center justify-center"
            style={{
              backfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
            }}
          >
            <div className="text-white text-center">
              <h3 className="text-2xl font-bold mb-4">How do you rate this?</h3>
              <p className="text-sm mb-6 italic">{currentFragrance.description}</p>

              {/* Star Rating */}
              <div className="flex justify-center gap-2 mb-6">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRating(star);
                    }}
                    className={`text-4xl transition ${
                      rating >= star ? 'text-yellow-300' : 'text-white/30'
                    }`}
                  >
                    ⭐
                  </button>
                ))}
              </div>

              {/* Notes Info */}
              <div className="text-left bg-white/10 rounded-lg p-4">
                <p className="text-xs font-semibold mb-2">TOP NOTES</p>
                <p className="text-xs mb-3">{currentFragrance.top_notes?.join(', ')}</p>
                
                <p className="text-xs font-semibold mb-2">MIDDLE NOTES</p>
                <p className="text-xs mb-3">{currentFragrance.middle_notes?.join(', ')}</p>
                
                <p className="text-xs font-semibold mb-2">BASE NOTES</p>
                <p className="text-xs">{currentFragrance.base_notes?.join(', ')}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="mt-8 flex gap-4">
        <button
          onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
          disabled={currentIndex === 0}
          className="px-6 py-2 bg-white/20 text-white rounded-lg disabled:opacity-50 hover:bg-white/30 transition"
        >
          ← Previous
        </button>
        <button
          onClick={() => setCurrentIndex(currentIndex + 1)}
          className="px-6 py-2 bg-[#d4a574] text-white rounded-lg hover:bg-[#c9935f] transition"
        >
          Skip →
        </button>
      </div>
    </div>
  );
};

export default FlashcardQuiz;
