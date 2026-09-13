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
        <p className="text-[9px] uppercase tracking-widest text-white/35 mb-2">
          1–10 scale · 1–4 Dislike · 5 Neutral · 6–10 Like
        </p>
      )}
      <div className="flex gap-2">
        {RATING_OPTIONS.map(({ label, value, range }) => (
          <button
            key={value}
            onClick={(e) => handleSelectRating(e, value)}
            className={`flex-1 text-[10px] font-bold uppercase tracking-wider px-2 py-2 rounded-lg border transition-colors ${
              currentRating === value
                ? 'bg-amber-500/20 border-amber-500/40 text-amber-200'
                : 'bg-white/5 border-white/10 text-white/60 hover:text-white hover:bg-white/10'
            }`}
            aria-pressed={currentRating === value}
          >
            {label} ({range})
          </button>
        ))}
      </div>
    </div>
  );
}