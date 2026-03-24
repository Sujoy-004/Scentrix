'use client';

import { useEffect, useRef } from 'react';

export function HowItWorks() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-fade-in');
        }
      });
    }, { threshold: 0.1 });

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
      const cards = sectionRef.current.querySelectorAll('.step-card');
      cards.forEach((card) => observer.observe(card));
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section className="how-it-works" ref={sectionRef}>
      <div className="how-it-works-container">
        <div className="section-header">
          <h2 className="section-title">How It Works</h2>
          <p className="section-subtitle">Discover your perfect fragrance in three simple steps</p>
        </div>

        <div className="steps-grid">
          <div className="step-card step-1">
            <div className="step-number">1</div>
            <div className="step-emoji">⭐</div>
            <h3 className="step-heading">Rate Your Favorites</h3>
            <p className="step-description">
              Answer quick questions about your favorite fragrances. Rate them on sweetness, woodiness, longevity, and intensity.
            </p>
            <div className="step-visual">🎯</div>
          </div>

          <div className="step-card step-2">
            <div className="step-number">2</div>
            <div className="step-emoji">🧠</div>
            <h3 className="step-heading">Get AI-Matched</h3>
            <p className="step-description">
              Our GraphSAGE AI analyzes your taste profile and compares it with 1000+ fragrances from our carefully curated database.
            </p>
            <div className="step-visual">🔄</div>
          </div>

          <div className="step-card step-3">
            <div className="step-number">3</div>
            <div className="step-emoji">✨</div>
            <h3 className="step-heading">Explore & Discover</h3>
            <p className="step-description">
              Browse personalized matches, view detailed notes, read community reviews, and save your favorites to your collection.
            </p>
            <div className="step-visual">🎁</div>
          </div>
        </div>
      </div>
    </section>
  );
}
