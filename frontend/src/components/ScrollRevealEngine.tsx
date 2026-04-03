'use client';

import { useEffect } from 'react';

export default function ScrollRevealEngine() {
  useEffect(() => {
    // Reveal once trigger - feels more premium for "Quiet Luxury"
    const observerOptions = {
      root: null,
      rootMargin: '0px 0px -80px 0px', // Trigger slightly before the element fully hits viewport
      threshold: 0.15,
    };

    const handleIntersect = (entries: IntersectionObserverEntry[], observer: IntersectionObserver) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-inview');
          // For high-density pages, we unobserve after the first reveal to save CPU
          observer.unobserve(entry.target);
        }
      });
    };

    const observer = new IntersectionObserver(handleIntersect, observerOptions);

    // Initial scan
    const scan = () => {
      const revealElements = document.querySelectorAll('.scroll-reveal:not(.is-inview)');
      revealElements.forEach((el) => observer.observe(el));
    };

    scan();

    // Mutation Observer to handle dynamic content (e.g. hydration delays)
    const mutationObserver = new MutationObserver((mutations) => {
      let needsScan = false;
      mutations.forEach((mutation) => {
        if (mutation.addedNodes.length > 0) needsScan = true;
      });
      if (needsScan) scan();
    });

    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });

    // Special trigger for the Hero (immediate reveal)
    const forceHero = () => {
      const hero = document.querySelector('.hero-section .scroll-reveal');
      if (hero) hero.classList.add('is-inview');
    };
    
    // Tiny delay to ensure hydration is stable
    const heroTimer = setTimeout(forceHero, 150);

    return () => {
      observer.disconnect();
      mutationObserver.disconnect();
      clearTimeout(heroTimer);
    };
  }, []);

  return null;
}
