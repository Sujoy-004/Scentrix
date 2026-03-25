'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { getFeaturedFragrances } from '@/lib/mockData';

export function ProductGrid() {
  const router = useRouter();
  const sectionRef = useRef<HTMLDivElement>(null);

  // Load actual fragrances from mock data (first 6 featured)
  const featuredFragrances = getFeaturedFragrances(6);
  
  // Use static, deterministic data to avoid hydration mismatches
  const staticMetrics = [
    { rating: 4.8, reviews: 342, match: 89 },
    { rating: 4.9, reviews: 856, match: 92 },
    { rating: 4.7, reviews: 621, match: 85 },
    { rating: 4.8, reviews: 504, match: 91 },
    { rating: 4.6, reviews: 418, match: 87 },
    { rating: 4.7, reviews: 533, match: 88 },
  ];
  
  const fragrances = featuredFragrances.map((frag: any, idx: number) => ({
    id: frag.id,
    brand: frag.brand,
    name: frag.name,
    notes: frag.top_notes?.slice(0, 3) || [],
    rating: staticMetrics[idx]?.rating || 4.5,
    reviews: staticMetrics[idx]?.reviews || 300,
    match: (staticMetrics[idx]?.match || 80) + '%',
  }));

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
      const cards = sectionRef.current.querySelectorAll('.fragrance-card');
      cards.forEach((card) => observer.observe(card));
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section className="product-grid" ref={sectionRef}>
      <div className="product-grid-container">
        <div className="section-header">
          <h2 className="section-title">Discover Premium Fragrances</h2>
          <p className="section-subtitle">Handpicked fragrances from the world's finest brands</p>
        </div>

        <div className="fragrances-grid">
          {fragrances.map((fragrance, index) => (
            <div key={index} className="fragrance-card">
              <div className="fragrance-image">🧴</div>
              
              <div className="fragrance-content">
                <div className="fragrance-brand">{fragrance.brand}</div>
                <h3 className="fragrance-name">{fragrance.name}</h3>
                
                <div className="fragrance-notes">
                  {fragrance.notes.map((note: string, i: number) => (
                    <span key={i} className="note-pill">{note}</span>
                  ))}
                </div>

                <div className="fragrance-rating">
                  <span className="stars">{'⭐'.repeat(Math.floor(fragrance.rating))}</span>
                  <span className="rating-count">({fragrance.reviews})</span>
                </div>

                <div className="fragrance-match">
                  <span className="match-label">Your Match</span>
                  <span className="match-score">{fragrance.match}</span>
                </div>

                <button 
                  className="fragrance-btn"
                  onClick={() => router.push(`/fragrances/${fragrance.id}`)}
                >
                  View Details
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
