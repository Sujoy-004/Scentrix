'use client';

import { useEffect } from 'react';

interface Particle {
  id: string;
  x: number;
  y: number;
  angle: number;
  velocity: number;
}

export function ClickSprayEffect() {
  useEffect(() => {
    const particles: Particle[] = [];
    let particleId = 0;

    const createParticle = (clientX: number, clientY: number) => {
      const numParticles = 12; // Number of particles per click
      
      for (let i = 0; i < numParticles; i++) {
        const angle = (i / numParticles) * Math.PI * 2;
        const velocity = 2 + Math.random() * 3; // Random velocity
        
        const particle: Particle = {
          id: `particle-${particleId++}`,
          x: clientX,
          y: clientY,
          angle,
          velocity,
        };

        // Create DOM element
        const el = document.createElement('div');
        el.id = particle.id;
        el.className = 'spray-particle';
        el.style.left = `${clientX}px`;
        el.style.top = `${clientY}px`;
        document.body.appendChild(el);

        particles.push(particle);

        // Animate the particle
        let startTime = Date.now();
        const duration = 800; // Duration in ms

        const animate = () => {
          const elapsed = Date.now() - startTime;
          const progress = elapsed / duration;

          if (progress >= 1) {
            // Remove particle from DOM
            el.remove();
            // Remove from array
            const index = particles.indexOf(particle);
            if (index > -1) particles.splice(index, 1);
            return;
          }

          // Calculate position
          const distance = particle.velocity * progress * 100;
          const x = Math.cos(particle.angle) * distance;
          const y = Math.sin(particle.angle) * distance;

          // Update position and opacity
          el.style.transform = `translate(${x}px, ${y}px)`;
          el.style.opacity = `${1 - progress}`;

          requestAnimationFrame(animate);
        };

        requestAnimationFrame(animate);
      }
    };

    const handleClick = (e: MouseEvent) => {
      // Only trigger on clicks that don't hit interactive elements
      const target = e.target as HTMLElement;
      const isInteractive =
        target.tagName === 'A' ||
        target.tagName === 'BUTTON' ||
        target.closest('a') ||
        target.closest('button') ||
        target.closest('input') ||
        target.closest('textarea');

      if (!isInteractive) {
        createParticle(e.clientX, e.clientY);
      }
    };

    document.addEventListener('click', handleClick);

    return () => {
      document.removeEventListener('click', handleClick);
      // Cleanup all particles
      particles.forEach((p) => {
        const el = document.getElementById(p.id);
        if (el) el.remove();
      });
    };
  }, []);

  return null;
}
