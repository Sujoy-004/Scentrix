'use client';

import { useEffect, useRef, useState } from 'react';

interface ScrollSequenceProps {
  frameCount: number;
  basePath: string;
  prefix?: string;
  extension?: string;
}

export function ScrollSequence({ 
  frameCount, 
  basePath, 
  prefix = 'ezgif-frame-', 
  extension = 'png',
  isFixed = true 
}: ScrollSequenceProps & { isFixed?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [images, setImages] = useState<HTMLImageElement[]>([]);
  const [loadedCount, setLoadedCount] = useState(0);

  // Preload images
  useEffect(() => {
    const preloadImages = async () => {
      const loadedImages: HTMLImageElement[] = [];
      let count = 0;

      for (let i = 1; i <= frameCount; i++) {
        const img = new Image();
        const frameNumber = i.toString().padStart(3, '0');
        img.src = `${basePath}/${prefix}${frameNumber}.${extension}`;
        img.onload = () => {
          count++;
          setLoadedCount(count);
        };
        loadedImages.push(img);
      }
      setImages(loadedImages);
    };

    preloadImages();
  }, [frameCount, basePath, prefix, extension]);

  // Handle scroll and draw
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || images.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const render = () => {
      const scrollTop = window.scrollY;
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const scrollFraction = Math.max(0, Math.min(1, scrollTop / maxScroll));
      
      const frameIndex = Math.min(
        frameCount - 1,
        Math.floor(scrollFraction * frameCount)
      );

      if (images[frameIndex] && images[frameIndex].complete) {
        const dpr = window.devicePixelRatio || 1;
        const w = window.innerWidth;
        const h = window.innerHeight;
        
        // High-DPI canvas sizing
        if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
          canvas.width = w * dpr;
          canvas.height = h * dpr;
          // Scale back CSS size
          canvas.style.width = `${w}px`;
          canvas.style.height = `${h}px`;
        }

        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const img = images[frameIndex];
        const canvasAspect = canvas.width / canvas.height;
        const imgAspect = img.width / img.height;

        let drawWidth, drawHeight, offsetX, offsetY;

        // Contain logic to prevent cropping
        if (canvasAspect > imgAspect) {
          // Screen is wider than image (landscape screen, portrait image)
          drawHeight = canvas.height;
          drawWidth = canvas.height * imgAspect;
          offsetX = (canvas.width - drawWidth) / 2;
          offsetY = 0;
        } else {
          // Screen is narrower than image (portrait screen, landscape image)
          drawWidth = canvas.width;
          drawHeight = canvas.width / imgAspect;
          offsetX = 0;
          offsetY = (canvas.height - drawHeight) / 2;
        }

        ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);
      }

      requestAnimationFrame(render);
    };

    const animationId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animationId);
  }, [images, frameCount]);

  const wrapperStyle: React.CSSProperties = isFixed ? {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100vw',
    height: '100dvh',
    zIndex: -1,
    pointerEvents: 'none',
    background: '#000' // True black floor for cinematic depth
  } : {
    position: 'sticky',
    top: 0,
    width: '100vw',
    height: '100dvh'
  };

  return (
    <>
      <div className="scroll-sequence-sticky" style={wrapperStyle}>
        <canvas 
          ref={canvasRef} 
          style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.95 }}
        />
        {loadedCount < frameCount && (
          <div className="sequence-loader" style={{ position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#161310', color: 'var(--amber-glow)', zIndex: 1000 }}>
            <div style={{ textAlign: 'center' }}>
              <p style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: '1.2rem', marginBottom: '10px' }}>Refining Essence...</p>
              <div style={{ width: '200px', height: '2px', background: 'rgba(212, 175, 55, 0.1)', position: 'relative' }}>
                <div style={{ position: 'absolute', top: 0, left: 0, height: '100%', background: 'var(--amber-glow)', width: `${(loadedCount / frameCount) * 100}%`, transition: 'width 0.3s ease' }} />
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
