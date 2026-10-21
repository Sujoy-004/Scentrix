'use client';

import React from 'react';
import { Skeleton, SkeletonMedia, SkeletonSheen, SkeletonText } from './Skeleton';

/**
 * Placeholder for `/fragrances/[id]`.
 *
 * Mirrors `app/fragrances/[id]/page.tsx`: a back link, a two-column grid
 * (bottle image left, metadata right), a row of meta chips, the note
 * pyramids, and the bordered rating panel.
 */
export function FragranceDetailSkeleton() {
  return (
    <div className="min-h-screen bg-black relative">
      <SkeletonSheen />

      <div className="relative z-10 mx-auto max-w-5xl px-6 py-8">
        {/* Back link */}
        <div className="mb-8 flex items-center gap-2">
          <Skeleton flat className="rounded-full" style={{ width: '0.85rem', height: '0.85rem' }} />
          <Skeleton flat className="rounded-full" style={{ width: '3rem', height: '0.6rem' }} />
        </div>

        <div className="grid md:grid-cols-2 gap-10 items-start">
          {/* Bottle image */}
          <div>
            <div
              className="relative aspect-[4/5] overflow-hidden rounded-3xl"
              style={{ border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <SkeletonMedia />
              {/* Family badge that floats over the image */}
              <Skeleton
                tone="accent-ghost"
                flat
                className="absolute top-4 left-4 rounded-full"
                style={{ width: '5rem', height: '1.75rem' }}
              />
            </div>
          </div>

          {/* Metadata column */}
          <div className="flex flex-col">
            {/* Brand */}
            <Skeleton
              tone="accent-ghost"
              flat
              className="rounded-full mb-2"
              style={{ width: '7rem', height: '0.65rem' }}
            />

            {/* Name — the real h1 is `font-display italic text-4xl` (~36px/line) */}
            <div className="mb-6">
              <Skeleton className="rounded-md mb-2" style={{ width: '20rem', maxWidth: '100%', height: '2.25rem' }} />
              <Skeleton className="rounded-md" style={{ width: '13rem', maxWidth: '100%', height: '2.25rem' }} />
            </div>

            {/* Meta chips: year, concentration, gender, rating */}
            <div className="flex flex-wrap gap-2 mb-8">
              {[3.5, 5, 4, 5.5].map((w, i) => (
                <Skeleton
                  key={i}
                  flat
                  tone={i === 3 ? 'accent' : 'base'}
                  className="rounded-full"
                  style={{ width: `${w}rem`, height: '1.7rem' }}
                />
              ))}
            </div>

            {/* Description */}
            <SkeletonText className="mb-8" widths={['92%', '96%', '58%']} height="0.85rem" />

            {/* Note pyramids: top / middle / base */}
            <div className="mb-8 space-y-4">
              {[0, 1, 2].map((group) => (
                <div key={group}>
                  <Skeleton
                    tone="accent-ghost"
                    flat
                    className="rounded-full mb-2"
                    style={{ width: '5.5rem', height: '0.6rem' }}
                  />
                  <div className="flex flex-wrap gap-2">
                    <Skeleton flat className="rounded-md" style={{ width: '4.5rem', height: '1.4rem' }} />
                    <Skeleton flat className="rounded-md" style={{ width: '3.5rem', height: '1.4rem' }} />
                    <Skeleton flat className="rounded-md" style={{ width: '5rem', height: '1.4rem' }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Rating panel */}
            <div
              className="mt-auto pt-4"
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '1.25rem',
                padding: '1.25rem',
              }}
            >
              <Skeleton flat className="rounded-full mb-3" style={{ width: '11rem', height: '0.6rem' }} />
              <div className="flex gap-2">
                {['Dislike', 'Neutral', 'Love'].map((label, i) => (
                  <Skeleton
                    key={label}
                    flat
                    tone={i === 2 ? 'accent-ghost' : 'base'}
                    className="rounded-full flex-1"
                    style={{ height: '2.25rem' }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default FragranceDetailSkeleton;
