'use client';

import React from 'react';
import { Skeleton, SkeletonCard, SkeletonSheen, SkeletonText } from './Skeleton';

/**
 * Placeholder for `/recommendations`.
 *
 * Mirrors `app/recommendations/page.tsx`: the discovery banner, the
 * centred results header, the stats band and the fragrance grid.
 */
export function RecommendationsSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="recommendations-page relative">
      <SkeletonSheen />

      <div className="container mx-auto px-6 relative z-10">
        {/* Discovery banner */}
        <div className="guest-auth-banner-elite">
          <div className="flex items-center gap-4">
            <Skeleton flat tone="accent-ghost" className="rounded-xl" style={{ width: '2.5rem', height: '2.5rem' }} />
            <div className="flex-1">
              <Skeleton flat className="rounded-full mb-1.5" style={{ width: '8rem', height: '0.7rem' }} />
              <Skeleton flat className="rounded-full" style={{ width: '16rem', maxWidth: '100%', height: '0.6rem' }} />
            </div>
            <div className="flex items-center gap-4">
              <Skeleton flat className="rounded-full" style={{ width: '11.875rem', height: '2.75rem' }} />
            </div>
          </div>
        </div>

        {/* Results header */}
        <header className="recommendations-header">
          <Skeleton
            tone="accent-ghost"
            flat
            className="rounded-full mx-auto"
            style={{ width: '9rem', height: '0.7rem' }}
          />
          {/* The real h1 is clamp(2.5rem, 5vw, 4rem) italic */}
          <Skeleton
            className="rounded-xl mx-auto"
            style={{ width: '24rem', maxWidth: '85%', height: '3.75rem', marginTop: '1.25rem' }}
          />
          <SkeletonText
            className="mx-auto mt-4"
            align="center"
            widths={['30rem', '22rem']}
            height="0.85rem"
          />
        </header>

        {/* State indicator — reuses the real panel shell so the padding,
            border and radius match exactly */}
        <div className="state-indicator">
          <div className="state-indicator-header">
            <Skeleton flat tone="accent-ghost" className="rounded-full" style={{ width: '7.5rem', height: '1.5rem' }} />
          </div>
          <Skeleton flat className="rounded-full mb-2" style={{ width: '22rem', maxWidth: '100%', height: '0.8rem' }} />
          <Skeleton flat className="rounded-full mb-3" style={{ width: '14rem', maxWidth: '100%', height: '0.7rem' }} />
          <Skeleton flat className="rounded-full" style={{ width: '20rem', maxWidth: '100%', height: '0.7rem' }} />
        </div>

        {/* Stats band */}
        <div className="recommendations-stats-elite">
          <div style={{ textAlign: 'center' }}>
            <Skeleton className="rounded-md mx-auto" style={{ width: '3.5rem', height: '2rem' }} />
            <Skeleton flat className="rounded-full mx-auto mt-2" style={{ width: '4.5rem', height: '0.6rem' }} />
          </div>
        </div>

        {/* Results grid */}
        <h2 id="recs-heading-skeleton" className="sr-only">
          Recommended fragrances
        </h2>
        <div className="recommendations-grid-elite" aria-labelledby="recs-heading-skeleton">
          {Array.from({ length: count }).map((_, i) => (
            <SkeletonCard key={i} withReason={i < 2} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default RecommendationsSkeleton;
