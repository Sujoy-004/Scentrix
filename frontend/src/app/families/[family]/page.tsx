'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getFragrancesByFamily } from '@/lib/mockData';
import '../../fragrances/fragrances.css';
import './family.css';

export default function FamilyPage({
  params,
}: {
  params: { family: string };
}) {
  const router = useRouter();
  const sectionRef = useRef<HTMLDivElement>(null);
  const [sortBy, setSortBy] = useState<'rating' | 'name' | 'match'>('rating');

  // Load fragrances from mock data
  const fragrances = getFragrancesByFamily(params.family);
  const isLoading = false;
  const error = fragrances.length === 0 ? 'No fragrances found' : null;

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-fade-in');
        }
      });
    });

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
      const cards = sectionRef.current.querySelectorAll('.fragrance-list-card');
      cards.forEach((card, index) => {
        (card as HTMLElement).style.animationDelay = `${index * 0.03}s`;
        observer.observe(card);
      });
    }

    return () => observer.disconnect();
  }, []);

  const allFragrances = fragrances || [];

  // Add computed properties for display - use deterministic values to avoid hydration issues
  const fragrancesWithMetrics = allFragrances.map((frag: any, idx: number) => {
    // Use fragrance index to get deterministic values instead of random
    const ratingBase = [4.8, 4.9, 4.7, 4.8, 4.6, 4.7, 4.5, 4.9][idx % 8] || 4.5;
    const matchBase = [89, 92, 85, 91, 87, 88, 80, 90][idx % 8] || 80;
    
    return {
      ...frag,
      rating: ratingBase.toFixed(1),
      match_score: matchBase,
    };
  });

  const sortedFragrances = [...fragrancesWithMetrics].sort((a: any, b: any) => {
    if (sortBy === 'rating') return parseFloat(b.rating) - parseFloat(a.rating);
    if (sortBy === 'name') return (a.name || '').localeCompare(b.name || '');
    if (sortBy === 'match') return b.match_score - a.match_score;
    return 0;
  });

  const familyNames: Record<string, string> = {
    floral: '🌸 Floral',
    woody: '🌲 Woody',
    citrus: '🍊 Citrus',
    amber: '🍯 Amber',
    aromatic: '🌿 Aromatic',
    fruity: '🍓 Fruity',
    chypre: '✨ Chypré',
    aquatic: '💧 Aquatic',
  };

  const familyName = familyNames[params.family.toLowerCase()] || params.family;

  if (isLoading) {
    return (
      <div className="fragrances-loading">
        <div className="loading-spinner">
          <p>Loading {familyName} fragrances...</p>
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fragrances-error">
        <h2>Unable to load fragrances</h2>
        <p>Please try again later.</p>
        <button
          className="error-button"
          onClick={() => router.push('/fragrances')}
        >
          Back to All Fragrances
        </button>
      </div>
    );
  }

  return (
    <div className="fragrances-page">
      <div className="fragrances-container">
        {/* Header */}
        <div className="fragrances-header">
          <div>
            <h1>{familyName} Fragrances</h1>
            <p>
              Explore {sortedFragrances.length} fragrance
              {sortedFragrances.length !== 1 ? 's' : ''} in this family
            </p>
          </div>
          <button
            className="back-to-home"
            onClick={() => router.push('/fragrances')}
          >
            ← All Fragrances
          </button>
        </div>

        {/* Sort Controls */}
        <div className="controls-section family-controls">
          <div className="sort-group">
            <label>Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'rating' | 'name' | 'match')}
              className="sort-select"
            >
              <option value="rating">Highest Rated</option>
              <option value="match">Best Match</option>
              <option value="name">Alphabetical</option>
            </select>
          </div>

          <div className="result-count">
            Showing {sortedFragrances.length} fragrance
            {sortedFragrances.length !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Family Description */}
        <div className="family-description">
          <p className="description-text">
            {params.family === 'floral'
              ? 'Delicate, romantic, and elegant. Floral fragrances celebrate the beauty of flowers with notes like roses, jasmine, and gardenias.'
              : params.family === 'woody'
              ? 'Rich, warm, and grounding. Woody fragrances feature deep base notes from sandalwood, cedar, and vetiver.'
              : params.family === 'citrus'
              ? 'Bright, fresh, and energizing. Citrus fragrances open with zesty top notes of bergamot, lemon, and orange.'
              : params.family === 'amber'
              ? 'Sweet, sensual, and warm. Amber fragrances create a cozy aura with vanilla, tonka bean, and musk notes.'
              : params.family === 'aromatic'
              ? 'Fresh, herbal, and invigorating. Aromatic fragrances feature lavender, rosemary, and mint.'
              : params.family === 'fruity'
              ? 'Juicy, playful, and vibrant. Fruity fragrances burst with apple, peach, and berry notes.'
              : params.family === 'chypre'
              ? 'Classic, elegant, and timeless. Chypré fragrances blend citrus, florals, and woody base notes.'
              : 'Light, airy, and refreshing. Aquatic fragrances evoke the ocean with fresh, ozonic notes.'}
          </p>
        </div>

        {/* Fragrances Grid */}
        <div className="fragrances-grid" ref={sectionRef}>
          {sortedFragrances.map((fragrance: any, index: number) => (
            <div key={index} className="fragrance-list-card">
              <div className="card-emoji">🧴</div>

              <div className="card-content">
                <h3 className="card-title">{fragrance.name}</h3>
                <p className="card-brand">{fragrance.brand}</p>

                {fragrance.top_notes && (
                  <div className="card-notes">
                    <p className="notes-label">Top Notes</p>
                    <div className="notes-pills">
                      {fragrance.top_notes.slice(0, 2).map((note: string, i: number) => (
                        <span key={i} className="note-pill">
                          {note}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="card-metrics">
                  <div className="metric">
                    <span className="stars">⭐</span>
                    <span className="metric-value">{fragrance.rating || 4.5}</span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">Match</span>
                    <span className="metric-value">{fragrance.match_score || 78}%</span>
                  </div>
                </div>
              </div>

              <button
                className="card-button"
                onClick={() =>
                  router.push(`/fragrances/${fragrance.id || `frag-${index}`}`)
                }
              >
                View
              </button>
            </div>
          ))}
        </div>

        {sortedFragrances.length === 0 && (
          <div className="empty-state">
            <p>No fragrances found in this family.</p>
            <button
              className="error-button"
              onClick={() => router.push('/fragrances')}
            >
              View All Fragrances
            </button>
          </div>
        )}

        {/* Still Exploring */}
        <div className="still-exploring">
          <h2>Still Exploring?</h2>
          <p>Check out other fragrance families or take the quiz for personalized recommendations</p>
          <button
            className="explore-btn"
            onClick={() => router.push('/onboarding/quiz')}
          >
            Get Personalized Recommendations
          </button>
        </div>
      </div>
    </div>
  );
}
