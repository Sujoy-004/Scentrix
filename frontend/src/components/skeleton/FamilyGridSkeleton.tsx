'use client';

import React from 'react';
import { Skeleton, SkeletonCard, SkeletonSheen, SkeletonText } from './Skeleton';

/**
 * Placeholder for `/families/[family]`.
 *
 * Mirrors `app/families/[family]/page.tsx`: the centred family header
 * (back link, eyebrow, title, description, count) followed by the
 * fragrance card grid.
 */
export function FamilyGridSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="family-page relative">
      <SkeletonSheen />

      <div className="relative z-10">
        <div className="family-header">
          {/* Back link */}
          <Skeleton flat className="rounded-full inline-block mb-10" style={{ width: '6rem', height: '0.7rem' }} />

          {/* Eyebrow */}
          <Skeleton
            tone="accent-ghost"
            flat
            className="rounded-full mx-auto"
            style={{ width: '9rem', height: '0.7rem' }}
          />

          {/* Title — the real h1 is clamp(2.5rem, 6vw, 4.5rem) italic */}
          <Skeleton
            className="rounded-xl mx-auto"
            style={{ width: '22rem', maxWidth: '85%', height: '4rem', marginTop: '1.25rem' }}
          />

          {/* Description */}
          <SkeletonText
            className="mx-auto mt-6"
            align="center"
            widths={['26rem', '19rem']}
            height="0.9rem"
          />

          {/* Count */}
          <Skeleton
            tone="accent-ghost"
            flat
            className="rounded-full mx-auto"
            style={{ width: '8rem', height: '0.7rem', marginTop: '1.5rem' }}
          />
        </div>

        <div className="recommendations-grid-elite">
          {Array.from({ length: count }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default FamilyGridSkeleton;
