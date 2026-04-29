'use client';

import React, { use, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, type FragranceCatalogItem } from '@/lib/api';
import './family.css';

const FAMILY_NAMES: Record<string, string> = {
  amber: '🍯 Amber', animalic: '🐾 Animalic', aquatic: '💧 Aquatic', aromatic: '🌿 Aromatic', citrus: '🍊 Citrus',
  earthy: '🌍 Earthy', floral: '🌸 Floral', fresh: '❄️ Fresh', fruity: '🍓 Fruity', gourmand: '🧁 Gourmand',
  green: '🍃 Green', leather: '👞 Leather', musky: '☁️ Musky', oriental: '✨ Oriental', powdery: '💄 Powdery',
  smoky: '🔥 Smoky', spicy: '🌶️ Spicy', woody: '🌲 Woody'
};

const FAMILY_DESCRIPTIONS: Record<string, string> = {
  amber: 'Sweet, sensual, and warm. Amber fragrances create a cozy aura with vanilla, tonka bean, and musk notes.',
  animalic: 'Primitive, raw, and hypnotic. Animalic scents evoke natural magnetism with musky, leathery, and earthy undertones.',
  aquatic: 'Light, airy, and refreshing. Aquatic fragrances evoke the ocean with fresh, ozonic, and saline notes.',
  aromatic: 'Fresh, herbal, and invigorating. Aromatic fragrances feature lavender, rosemary, and sage.',
  citrus: 'Bright, fresh, and energizing. Citrus fragrances open with zesty top notes of bergamot, lemon, and orange.',
  earthy: 'Deep, damp, and natural. Earthy scents capture the essence of soil, moss, and forest floors.',
  floral: 'Delicate, romantic, and elegant. Floral fragrances celebrate the beauty of flowers like roses and jasmine.',
  fresh: 'Crisp, clean, and breezy. Fresh fragrances capture the lightness of mountain air and pure water.',
  fruity: 'Juicy, playful, and vibrant. Fruity fragrances burst with apple, peach, and tropical berry notes.',
  gourmand: 'Sweet, edible, and indulgent. Gourmand scents feature notes of chocolate, caramel, and vanilla.',
  green: 'Lush, leafy, and natural. Green fragrances evoke crushed leaves and freshly cut grass.',
  leather: 'Sleek, smoky, and sophisticated. Leather scents capture the rich aroma of fine suede and cured hides.',
  musky: 'Soft, powdery, and intimate. Musky fragrances create a second-skin feel with a clean, sensual depth.',
  oriental: 'Exotic, opulent, and spicy. Oriental fragrances blend warm resins with precious woods and spices.',
  powdery: 'Soft, vintage, and comforting. Powdery scents evoke fine cosmetics and clean linens.',
  smoky: 'Incenso, ash, and charcoal. Smoky fragrances provide a mysterious, deep, and primitive allure.',
  spicy: 'Vibrant, warm, and sharp. Spicy scents feature pepper, cardamom, cinnamon, and cloves.',
  woody: 'Rich, warm, and grounding. Woody fragrances feature deep notes of sandalwood, cedar, and vetiver.'
};

export default function FamilyPage({ params: paramsPromise }: { params: Promise<{ family: string }> }) {
  const params = use(paramsPromise);
  const router = useRouter();
  const sectionRef = useRef<HTMLDivElement>(null);
  const [sortBy, setSortBy] = useState<'rating' | 'name' | 'match'>('rating');
  const [fragrances, setFragrances] = useState<FragranceCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const page = await api.getFragranceCatalog(48, 0, { family: params.family });
        setFragrances(Array.isArray(page?.items) ? page.items : []);
      } catch {
        setError('Failed to load fragrances. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, [params.family]);

  useEffect(() => {
    if (!sectionRef.current) return;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) entry.target.classList.add('animate-fade-in');
      });
    });
    const cards = sectionRef.current.querySelectorAll('.fragrance-list-card');
    cards.forEach((card, index) => {
      (card as HTMLElement).style.animationDelay = `${index * 0.03}s`;
      observer.observe(card);
    });
    return () => observer.disconnect();
  }, [fragrances]);

  const sorted = [...fragrances].sort((a: FragranceCatalogItem, b: FragranceCatalogItem) => {
    const rA = a.rating ?? 0;
    const rB = b.rating ?? 0;
    const mA = a.popularity_score ?? 0;
    const mB = b.popularity_score ?? 0;
    if (sortBy === 'rating') return rB - rA;
    if (sortBy === 'name') return (a.name || '').localeCompare(b.name || '');
    if (sortBy === 'match') return mB - mA;
    return 0;
  });

  const familyName = FAMILY_NAMES[params.family.toLowerCase()] || params.family;

  if (isLoading) {
    return (
      <div className="fragrances-loading">
        <div className="loading-spinner">
          <p>Loading {familyName} fragrances...</p>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fragrances-error">
        <h2>Unable to load fragrances</h2>
        <p>{error}</p>
        <button className="error-button" onClick={() => router.push('/fragrances')}>
          Back to All Fragrances
        </button>
      </div>
    );
  }

  return (
    <div className="fragrances-page">
      <div className="fragrances-container">
        <div className="fragrances-header">
          <div>
            <h1>{familyName} Fragrances</h1>
            <p>Explore {sorted.length} fragrance{sorted.length !== 1 ? 's' : ''} in this family</p>
          </div>
          <button className="back-to-home" onClick={() => router.push('/fragrances')}>
            ← All Fragrances
          </button>
        </div>

        <div className="controls-section family-controls">
          <div className="sort-group">
            <label>Sort by:</label>
            <select
              value={sortBy}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSortBy(e.target.value as 'rating' | 'name' | 'match')}
              className="sort-select"
            >
              <option value="rating">Highest Rated</option>
              <option value="match">Best Match</option>
              <option value="name">Alphabetical</option>
            </select>
          </div>
          <div className="result-count">Showing {sorted.length} fragrance{sorted.length !== 1 ? 's' : ''}</div>
        </div>

        <div className="family-description">
          <p className="description-text">{FAMILY_DESCRIPTIONS[params.family.toLowerCase()] || ''}</p>
        </div>

        <div className="fragrances-grid" ref={sectionRef}>
          {sorted.map((fragrance: FragranceCatalogItem, index: number) => (
            <div key={fragrance.id || index} className="fragrance-list-card">
              <div className="card-emoji">🧴</div>
              <div className="card-content">
                <h3 className="card-title">{fragrance.name}</h3>
                <p className="card-brand">{fragrance.brand}</p>
                {fragrance.top_notes && (
                  <div className="card-notes">
                    <p className="notes-label">Top Notes</p>
                    <div className="notes-pills">
                      {fragrance.top_notes.slice(0, 2).map((note: string, i: number) => (
                        <span key={i} className="note-pill">{note}</span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="card-metrics">
                  <div className="metric">
                    <span className="stars">⭐</span>
                    <span className="metric-value">{fragrance.rating ?? '4.5'}</span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">Match</span>
                    <span className="metric-value">{Math.round(fragrance.popularity_score ?? 85)}%</span>
                  </div>
                </div>
              </div>
              <button
                className="card-button"
                onClick={() => router.push(`/fragrances/${fragrance.id}`)}
              >
                View
              </button>
            </div>
          ))}
        </div>

        {sorted.length === 0 && (
          <div className="empty-state">
            <p>No fragrances found in this family.</p>
            <button className="error-button" onClick={() => router.push('/fragrances')}>
              View All Fragrances
            </button>
          </div>
        )}

        <div className="still-exploring" style={{ marginTop: '4rem', textAlign: 'center' }}>
          <h2>Still Exploring?</h2>
          <p>Check out other fragrance families or take the quiz for personalized recommendations</p>
          <button className="explore-btn" onClick={() => router.push('/onboarding/quiz')}>
            Get Personalized Recommendations
          </button>
        </div>
      </div>
    </div>
  );
}
