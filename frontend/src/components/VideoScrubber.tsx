'use client';

import { useEffect, useRef } from 'react';

interface VideoScrubberProps {
  videoPath: string;
  isFixed?: boolean;
  /**
   * How the video is mapped onto the canvas.
   * 'cover'   - fill the canvas, cropping the overflow (default).
   * 'contain' - fit the whole frame inside the canvas, letterboxing the rest.
   *             The original ScrollSequence used 'contain'.
   */
  fit?: 'cover' | 'contain';
  /**
   * When set, the video is scrubbed by this element's own scroll progress
   * instead of the page's. Use it to pin a video to a section so it plays
   * out while that section scrolls past.
   */
  container?: React.RefObject<HTMLElement | null>;
}

export function VideoScrubber({
  videoPath,
  isFixed = true,
  fit = 'cover',
  container,
}: VideoScrubberProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLElement | null>(null);

  // State for smoothing (Lerp)
  const state = useRef({
    targetTime: 0,
    currentTime: 0,
    smoothing: 0.1, // Adjusted for Next.js reactivity
  });

  useEffect(() => {
    containerRef.current = container?.current ?? null;
  }, [container]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    // Handle high-DPI displays
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
    };
    window.addEventListener('resize', resize);
    resize();

    const render = () => {
      const { targetTime, smoothing } = state.current;

      // Interpolate current time for "gliding" effect
      state.current.currentTime += (targetTime - state.current.currentTime) * smoothing;

      // Update video time (browser-throttled seek)
      if (video.readyState >= 2 && isFinite(state.current.currentTime) && isFinite(video.duration)) {
        // Clamp to safe range [0, duration]
        video.currentTime = Math.max(0, Math.min(video.duration, state.current.currentTime));

        // Manual draw to canvas to control scaling and performance
        const vRatio = video.videoWidth / video.videoHeight;
        const cRatio = canvas.width / canvas.height;

        let drawW = canvas.width;
        let drawH = canvas.height;
        let offX = 0;
        let offY = 0;

        if (fit === 'contain') {
          // Fit the whole frame, letterboxing the remainder.
          if (cRatio > vRatio) {
            drawH = canvas.height;
            drawW = canvas.height * vRatio;
            offX = (canvas.width - drawW) / 2;
            offY = 0;
          } else {
            drawW = canvas.width;
            drawH = canvas.width / vRatio;
            offX = 0;
            offY = (canvas.height - drawH) / 2;
          }
        } else if (cRatio > vRatio) {
          drawH = canvas.width / vRatio;
          offY = (canvas.height - drawH) / 2;
        } else {
          drawW = canvas.height * vRatio;
          offX = (canvas.width - drawW) / 2;
        }

        ctx.drawImage(video, offX, offY, drawW, drawH);
      }

      requestAnimationFrame(render);
    };

    const onScroll = () => {
      let scrollFraction: number;

      const host = containerRef.current;
      if (host) {
        // Section-scoped: 0 when the host's top reaches the viewport top,
        // 1 when its bottom reaches the viewport bottom.
        const rect = host.getBoundingClientRect();
        const travel = rect.height - window.innerHeight;
        scrollFraction = travel > 0 ? Math.max(0, Math.min(1, -rect.top / travel)) : 0;
      } else {
        const scrollTop = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        scrollFraction = docHeight > 0 ? Math.max(0, Math.min(1, scrollTop / docHeight)) : 0;
      }

      if (!video.duration) return;

      // Only seek into the part of the video that has actually been buffered.
      //
      // A Worker that serves static assets without HTTP Range support cannot
      // seek into bytes it has not downloaded yet: the browser silently clamps
      // currentTime to the buffered range, so the animation appears frozen
      // until the whole file arrives. Clamping to the buffered edge keeps the
      // scrub continuous and lets it catch up as the download proceeds.
      let limit = video.duration;
      if (video.buffered.length > 0) {
        limit = video.buffered.end(video.buffered.length - 1);
      }

      state.current.targetTime = Math.min(scrollFraction * video.duration, limit);
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    const rafId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(rafId);
    };
  }, [fit]);

  return (
    <div
      style={
        isFixed
          ? {
              position: 'fixed',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100dvh',
              zIndex: -1,
              pointerEvents: 'none',
              background: '#000',
              overflow: 'hidden'
            }
          : {
              // Fill the positioned parent and stay out of the flow. A sticky
              // element would still occupy layout space and push the
              // parent's other children below the fold.
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              zIndex: -1,
              pointerEvents: 'none',
              background: '#000',
              overflow: 'hidden'
            }
      }
    >
      <video
        ref={videoRef}
        preload="auto"
        muted
        playsInline
        style={{ display: 'none' }}
      >
        <source src={videoPath} type="video/mp4" />
      </video>
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          display: 'block'
        }}
      />
    </div>
  );
}
