'use client';

import { useEffect, useRef } from 'react';

export function ProductGrid() {
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
      const cards = sectionRef.current.querySelectorAll('.fragrance-card');
      cards.forEach((card) => observer.observe(card));
    }

    return () => observer.disconnect();
  }, []);

  const fragrances = [
    {
      brand: 'Gucci',
      name: 'Bloom',
      notes: ['Tuberose', 'Freesia', 'Amber'],
      rating: 4.8,
      reviews: 342,
      match: '89%',
    },
    {
      brand: 'Chanel',
      name: 'No. 5',
      notes: ['Ylang-ylang', 'Rose', 'Sandalwood'],
      rating: 4.9,
      reviews: 856,
      match: '92%',
    },
    {
      brand: 'Dior',
      name: 'J\'adore',
      notes: ['Jasmine', 'Rose', 'Violet'],
      rating: 4.7,
      reviews: 621,
      match: '85%',
    },
    {
      brand: 'Tom Ford',
      name: 'Black Orchid',
      notes: ['Orchid', 'Spicy Notes', 'Musk'],
      rating: 4.8,
      reviews: 504,
      match: '91%',
    },
    {
      brand: 'Yves Saint Laurent',
      name: 'Mon Paris',
      notes: ['Strawberry', 'Raspberry', 'Tuberose'],
      rating: 4.6,
      reviews: 418,
      match: '87%',
    },
    {
      brand: 'Prada',
      name: 'L\'Homme',
      notes: ['Iris', 'Cardamom', 'Amber'],
      rating: 4.7,
      reviews: 533,
      match: '88%',
    },
  ];

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
                  {fragrance.notes.map((note, i) => (
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

                <button className="fragrance-btn">View Details</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
