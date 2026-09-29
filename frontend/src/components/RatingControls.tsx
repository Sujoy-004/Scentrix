'use client';

import React from 'react';
import { useAppStore } from '@/stores/app-store';
import { useToastStore } from '@/stores/toast-store';

export interface RatingTarget {
  fragrance_id: string;
  name?: string;
  brand?: string;
  top_notes?: string[];
  accords?: string[];
}

const RATING_OPTIONS = [
  { label: 'Dislike', value: 3, range: '1–4' },
  { label: 'Neutral', value: 5, range: '5' },
  { label: 'Love', value: 9, range: '6–10' },
];

export function RatingControls({ target, scaleHint = true }: { target: RatingTarget; scaleHint?: boolean }) {
  const { quizResponses, addQuizResponse } = useAppStore();
  const addToast = useToastStore((s) => s.addToast);

  const current = quizResponses.find((r) => r.fragrance_id === target.fragrance_id);
  const currentRating = current?.rating ?? null;

  const handleSelectRating = (e: React.MouseEvent, value: number) => {
    e.stopPropagation();
    addQuizResponse({
      fragrance_id: target.fragrance_id,
      rating: value,
      name: target.name,
      brand: target.brand,
      top_notes: target.top_notes,
      accords: target.accords,
    });
    addToast({
      message: `Rated ${target.name || 'fragrance'} — refining your matches`,
      type: 'success',
    });
  };

  return (
    <div className="rating-controls" onClick={(e) => e.stopPropagation()}>
      {scaleHint && (
        <p className="rec-text-dim rec-fs-xs mb-2">
          Rate 1–10 · 1–4 dislike, 5 neutral, 6–10 like
        </p>
      )}
      <div
        className="flex gap-2"
        role="group"
        aria-label={`Rate ${target.name || 'this fragrance'} from 1 to 10`}
      >
        {RATING_OPTIONS.map(({ label, value, range }) => (
          <button
            key={value}
            onClick={(e) => handleSelectRating(e, value)}
            className="rating-option"
            aria-pressed={currentRating === value}
          >
            {label} <span className="rec-text-dim">({range})</span>
          </button>
        ))}
      </div>
    </div>
  );
}