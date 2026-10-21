'use client';

import { useEffect, useRef } from 'react';

interface VideoScrubberProps {
  videoPath: string;
  isFixed?: boolean;
}

export function VideoScrubber({ 
  videoPath, 
  isFixed = true 
}: VideoScrubberProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // State for smoothing (Lerp)
  const state = useRef({
    targetTime: 0,
    currentTime: 0,
    smoothing: 0.1, // Adjusted for Next.js reactivity
  });

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

        if (cRatio > vRatio) {
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
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollFraction = docHeight > 0 ? Math.max(0, Math.min(1, scrollTop / docHeight)) : 0;
      
      // Map scroll to video duration
      if (video.duration) {
        state.current.targetTime = scrollFraction * video.duration;
      }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    const rafId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <div 
      style={{
        position: isFixed ? 'fixed' : 'sticky',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100dvh',
        zIndex: -1,
        pointerEvents: 'none',
        background: '#000',
        overflow: 'hidden'
      }}
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
