'use client';

import React from 'react';

export type SkeletonTone = 'base' | 'accent' | 'accent-ghost';

interface SkeletonProps {
  /** Extra classes. */
  className?: string;
  /**
   * `base` — neutral placeholder.
   * `accent` — a filled amber chip (primary CTA, headline rule).
   * `accent-ghost` — a barely-there amber hint (metadata, counts).
   */
  tone?: SkeletonTone;
  /** Drop the shimmer sweep. Use for dense clusters of tiny blocks. */
  flat?: boolean;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

/**
 * The single primitive every skeleton is built from: a dim, hairline-bordered
 * block with a slow diagonal sheen sweeping across it.
 */
export function Skeleton({
  className = '',
  tone = 'base',
  flat = false,
  style,
  children,
}: SkeletonProps) {
  const classes = [
    'sk-block',
    tone !== 'base' ? `sk-block--${tone}` : '',
    flat ? 'sk-block--flat' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div aria-hidden="true" className={classes} style={style}>
      {children}
    </div>
  );
}

interface SkeletonFrameProps {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

/** The glass card shell — mirrors `.fragrance-card-elite` exactly. */
export function SkeletonFrame({ className = '', style, children }: SkeletonFrameProps) {
  return (
    <div aria-hidden="true" className={`sk-frame ${className}`} style={style}>
      {children}
    </div>
  );
}

/**
 * The image well that stands in for a fragrance photo, with a bottle
 * silhouette so it reads as "a photo is coming" rather than "broken".
 */
export function SkeletonMedia({ className = '' }: { className?: string }) {
  return (
    <div aria-hidden="true" className={`sk-media ${className}`}>
      <div className="sk-bottle">
        <div className="sk-bottle-cap" />
        <div className="sk-bottle-neck" />
        <div className="sk-bottle-body" />
      </div>
    </div>
  );
}

interface SkeletonTextProps {
  /** One width per line, as CSS lengths — e.g. ['26rem', '19rem']. */
  widths: string[];
  /** Height of each line bar. */
  height?: string;
  /** `start` for body copy, `center` for centred copy. */
  align?: 'start' | 'center';
  className?: string;
}

/**
 * A stack of placeholder lines that stands in for a paragraph.
 * Widths are explicit lengths rather than percentages so they never
 * resolve against the parent container.
 */
export function SkeletonText({
  widths,
  height = '0.75rem',
  align = 'start',
  className = '',
}: SkeletonTextProps) {
  return (
    <div
      aria-hidden="true"
      className={`flex flex-col gap-2 ${align === 'center' ? 'items-center' : 'items-start'} ${className}`}
    >
      {widths.map((w, i) => (
        <Skeleton
          key={i}
          flat
          className="rounded-full"
          style={{ width: w, height, maxWidth: '100%' }}
        />
      ))}
    </div>
  );
}

/**
 * The ambient sheen that sweeps the whole composition. Rendered once per
 * screen, behind everything.
 */
export function SkeletonSheen() {
  return <div aria-hidden="true" className="sk-sheen" />;
}

interface SkeletonCardProps {
  /** Optional extra class for the card frame. */
  className?: string;
  /** Show the 4/5 image block that tops every fragrance card. */
  withImage?: boolean;
  /** Show the "why recommended" panel that appears once you have ratings. */
  withReason?: boolean;
}

/**
 * A placeholder for one fragrance card — the unit repeated across the
 * family grid and the recommendations grid. Mirrors `FragranceCard`.
 */
export function SkeletonCard({ className = '', withImage = true, withReason = false }: SkeletonCardProps) {
  return (
    <SkeletonFrame className={`flex flex-col ${className}`}>
      {withImage && (
        <div className="relative aspect-[4/5] overflow-hidden">
          <SkeletonMedia />
          {/* Floating family badge that sits on the real card's image. */}
          <Skeleton
            tone="accent-ghost"
            flat
            className="absolute top-4 left-4 rounded-full"
            style={{ width: '4.5rem', height: '1.6rem' }}
          />
        </div>
      )}

      <div className="p-6 flex flex-col flex-1">
        <Skeleton flat className="rounded-full" style={{ width: '35%', height: '0.6rem' }} />
        <Skeleton className="rounded-md mt-2" style={{ width: '75%', height: '1.15rem' }} />

        <div className="flex flex-wrap gap-2 mt-4">
          <Skeleton flat tone="accent-ghost" className="rounded-md" style={{ width: '4rem', height: '1.4rem' }} />
          <Skeleton flat tone="accent-ghost" className="rounded-md" style={{ width: '3.2rem', height: '1.4rem' }} />
        </div>

        {withReason && (
          <div className="mt-5 p-4 rounded-xl">
            <Skeleton flat tone="accent-ghost" className="rounded-full" style={{ width: '6rem', height: '0.55rem' }} />
            <SkeletonText className="mt-2.5" widths={['95%', '72%']} height="0.65rem" />
          </div>
        )}

        <div className="mt-auto flex items-center gap-2 pt-5">
          <Skeleton flat className="rounded-full" style={{ width: '2.5rem', height: '0.55rem' }} />
          <Skeleton flat className="rounded-full" style={{ width: '4.5rem', height: '0.55rem' }} />
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2">
          {[0, 1, 2].map((i) => (
            <Skeleton
              key={i}
              flat
              tone={i === 2 ? 'accent-ghost' : 'base'}
              className="rounded-full"
              style={{ height: '2rem' }}
            />
          ))}
        </div>
      </div>
    </SkeletonFrame>
  );
}
