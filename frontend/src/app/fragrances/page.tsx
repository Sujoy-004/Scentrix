'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getAllFragrances, getFragrancesByFamily } from '@/lib/mockData';
import './fragrances.css';
import './fragrances.css';

export default function FragrancesPage() {
  const router = useRouter();
  const sectionRef = useRef<HTMLDivElement>(null);
  const [sortBy, setSortBy] = useState<'rating' | 'name' | 'match'>('rating');
  const [filterFamily, setFilterFamily] = useState<string>('');

  // Load fragrances from mock data
  const allFragrances = filterFamily ? getFragrancesByFamily(filterFamily) : getAllFragrances();
  const isLoading = false;
  const error = null;

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

  const fragrances = allFragrances || [];

  // Add computed properties for display - use deterministic values to avoid hydration issues
  const fragrancesWithMetrics = fragrances.map((frag: any, idx: number) => {
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

  const families = ['Floral', 'Woody', 'Citrus', 'Amber', 'Aromatic', 'Fruity', 'Chypré', 'Aquatic'];

  if (isLoading) {
    return (
      <div className="fragrances-loading">
        <div className="loading-spinner">
          <p>Loading fragrances...</p>
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
          onClick={() => router.push('/')}
        >
          Back to Home
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
            <h1>Explore Our Fragrance Collection</h1>
            <p>Discover from our curated database of {fragrances.length} fragrances</p>
          </div>
          <button
            className="back-to-home"
            onClick={() => router.push('/')}
          >
            ← Back to Home
          </button>
        </div>

        {/* Filters and Sort */}
        <div className="controls-section">
          <div className="filter-group">
            <label>Fragrance Family:</label>
            <select
              value={filterFamily}
              onChange={(e) => setFilterFamily(e.target.value)}
              className="filter-select"
            >
              <option value="">All Families</option>
              {families.map((family) => (
                <option key={family} value={family.toLowerCase()}>
                  {family}
                </option>
              ))}
            </select>
          </div>

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
            Showing {sortedFragrances.length} fragrance{sortedFragrances.length !== 1 ? 's' : ''}
          </div>
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
            <p>No fragrances found. Try adjusting your filters.</p>
            <button
              className="error-button"
              onClick={() => setFilterFamily('')}
            >
              Clear Filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
