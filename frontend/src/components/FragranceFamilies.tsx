'use client';

import { useEffect, useRef } from 'react';

export function FragranceFamilies() {
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
      const cards = sectionRef.current.querySelectorAll('.family-card');
      cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        observer.observe(card);
      });
    }

    return () => observer.disconnect();
  }, []);

  const families = [
    { name: '🌸 Floral', notes: 'Roses, jasmine, lily', description: 'Delicate and feminine' },
    { name: '🌲 Woody', notes: 'Sandalwood, cedar, vetiver', description: 'Rich and warm' },
    { name: '🍊 Citrus', notes: 'Bergamot, lemon, orange', description: 'Bright and energizing' },
    { name: '🍯 Amber', notes: 'Vanilla, tonka bean, musk', description: 'Sweet and sensual' },
    { name: '🌿 Aromatic', notes: 'Lavender, rosemary, mint', description: 'Fresh and herbal' },
    { name: '🍓 Fruity', notes: 'Apple, peach, berries', description: 'Juicy and playful' },
    { name: '✨ Chypre', notes: 'Oakmoss, patchouli, citrus', description: 'Classic and elegant' },
    { name: '💧 Aquatic', notes: 'Marine, ozonic, fresh', description: 'Light and airy' },
  ];

  return (
    <section className="fragrance-families" ref={sectionRef}>
      <div className="fragrance-families-container">
        <div className="section-header">
          <h2 className="section-title">Explore Fragrance Families</h2>
          <p className="section-subtitle">Find your scent profile across these carefully curated families</p>
        </div>

        <div className="families-grid">
          {families.map((family, index) => (
            <div key={index} className="family-card">
              <div className="family-emoji">{family.name.charAt(0)}</div>
              <h3 className="family-name">{family.name}</h3>
              <p className="family-description">{family.description}</p>
              <div className="family-notes">{family.notes}</div>
              <button className="family-btn">Explore Family</button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
