'use client';

import { useRef } from 'react';

import { VideoScrubber } from '@/components/VideoScrubber';

/**
 * Scroll-driven showcase of the fragrance line-up.
 *
 * This is the original ScrollSequence restored: 240 frames of the collection
 * that resolve as you scroll. The frames used to be shipped as 100 MB of
 * individual PNGs; they are now encoded as a single 0.7 MB video and scrubbed
 * through the canvas, which is 140x smaller and behaves identically.
 */
export function ScrollShowcase() {
  const sectionRef = useRef<HTMLElement | null>(null);

  return (
    <section
      ref={sectionRef}
      className="relative w-full"
      style={{ height: '280vh' }}
      aria-label="Fragrance line-up, revealed as you scroll"
    >
      {/* No overflow-hidden on the section: an overflow ancestor turns the
          sticky child into a non-scrolling box, and the video would scroll
          away instead of pinning. */}
      <div className="sticky top-0 h-screen w-full overflow-hidden bg-black">
        <VideoScrubber
          videoPath="/assets/scroll_sequence.mp4"
          isFixed={false}
          fit="contain"
          container={sectionRef}
        />

        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-72 bg-gradient-to-t from-black/90 via-black/55 to-transparent" />

        <div className="pointer-events-none relative z-10 flex h-full flex-col items-center justify-end pb-16">
          <p className="flex items-center gap-3 text-[var(--fs-xs)] font-bold uppercase tracking-[0.3em] text-primary/80 glow-amber">
            The Line-Up
          </p>
          <p className="mt-4 max-w-md px-6 text-center text-sm font-light tracking-[0.15em] text-white/85">
            Two hundred and forty frames of the collection, resolving as you descend.
          </p>
        </div>
      </div>
    </section>
  );
}
