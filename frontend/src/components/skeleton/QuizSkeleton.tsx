'use client';

import React from 'react';
import { Skeleton } from './Skeleton';
import '@/app/quiz/quiz.css';

/**
 * Placeholder for the quiz question card.
 *
 * Mirrors the rating phase of `components/StandardQuiz.tsx`: the floating
 * progress header, the glass quiz card with its fragrance name, note
 * capsules, the rating slider, and the two footer buttons.
 */
export function QuizSkeleton() {
  return (
    <div className="quiz-page">
      <div className="quiz-background-fixed" />

      <div className="quiz-container relative">
        {/* Floating progress header */}
        <header className="quiz-meta-header">
          <div className="progress-indicator">
            <Skeleton flat className="rounded-full" style={{ width: '7rem', height: '0.65rem' }} />
            <div className="progress-bar-wrap">
              <div className="progress-bar-fill" style={{ width: '38%' }} />
            </div>
          </div>
        </header>

        {/* The card */}
        <div className="quiz-card">
          <section className="quiz-card-visual">
            <Skeleton flat className="rounded-full mx-auto" style={{ width: '6rem', height: '0.65rem' }} />

            {/* Fragrance name — the real h2 is font-display italic, up to 2.25rem */}
            <Skeleton
              className="rounded-lg mx-auto"
              style={{ width: '18rem', maxWidth: '90%', height: '2.25rem', marginTop: '1rem' }}
            />
            <Skeleton
              className="rounded-lg mx-auto"
              style={{ width: '12rem', maxWidth: '80%', height: '2.25rem', marginTop: '0.75rem' }}
            />

            <div className="notes-capsules-nexus">
              {[5.5, 4, 6, 4.5].map((w, i) => (
                <Skeleton
                  key={i}
                  flat
                  tone={i === 3 ? 'accent-ghost' : 'base'}
                  className="rounded-full"
                  style={{ width: `${w}rem`, height: '2.4rem' }}
                />
              ))}
            </div>
          </section>

          <section className="quiz-rating-interaction">
            <Skeleton
              flat
              className="rounded-full mx-auto"
              style={{ width: '13rem', height: '0.65rem', marginBottom: '2.5rem' }}
            />

            <div className="rating-slider-nexus">
              <div className="rating-readout">
                <Skeleton className="rounded-md" style={{ width: '3.75rem', height: '4.5rem' }} />
                <Skeleton flat className="rounded-full" style={{ width: '2rem', height: '1rem' }} />
              </div>

              {/* Slider track with a knob */}
              <div className="w-full relative" style={{ height: '2px', background: 'rgba(255,255,255,0.15)' }}>
                <div
                  className="absolute top-0 left-0 h-full"
                  style={{
                    width: '58%',
                    background: 'var(--quiz-accent, #f4bb92)',
                    boxShadow: '0 0 10px var(--quiz-accent, #f4bb92)',
                  }}
                />
                <Skeleton
                  flat
                  tone="accent-ghost"
                  className="absolute rounded-full"
                  style={{ width: '1.5rem', height: '1.5rem', left: '56%', top: '-0.69rem' }}
                />
              </div>

              <div className="flex justify-between w-full mt-1">
                {[3.5, 3, 3.5].map((w, i) => (
                  <Skeleton key={i} flat className="rounded-full" style={{ width: `${w}rem`, height: '0.55rem' }} />
                ))}
              </div>
            </div>
          </section>

          <footer className="quiz-controls-nexus">
            <Skeleton flat className="rounded-3xl" style={{ height: '3.5rem' }} />
            <Skeleton tone="accent" className="rounded-3xl" style={{ height: '3.5rem' }} />
          </footer>
        </div>

        <footer className="quiz-footer-meta">
          <div className="meta-badge">
            <Skeleton flat tone="accent-ghost" className="rounded-full" style={{ width: '9rem', height: '0.75rem' }} />
          </div>
        </footer>
      </div>
    </div>
  );
}

export default QuizSkeleton;
