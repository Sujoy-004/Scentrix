'use client';

import { useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getFragranceById } from '@/lib/mockData';
import { useAppStore } from '@/stores/app-store';
import './fragrance-detail.css';

export default function FragranceDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const view = searchParams.get('view');
  const sectionRef = useRef<HTMLDivElement>(null);

  // Load fragrance from mock data
  const fragrance = getFragranceById(params.id);
  const isLoading = false;
  const error = !fragrance;
  
  // Get store methods
  const { addToWishlist } = useAppStore();

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
    }

    return () => observer.disconnect();
  }, []);

  if (isLoading) {
    return (
      <div className="detail-loading">
        <div className="loading-spinner">
          <p>Loading fragrance details...</p>
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error || !fragrance) {
    return (
      <div className="detail-error">
        <h2>Fragrance not found</h2>
        <p>We couldn't find the fragrance you're looking for (ID: {params.id}).</p>
        <button
          className="error-button"
          onClick={() => router.push('/fragrances')}
        >
          Back to All Fragrances
        </button>
      </div>
    );
  }

  const notePyramid = {
    top: fragrance.top_notes || ['Bergamot', 'Lemon'],
    middle: fragrance.middle_notes || ['Jasmine', 'Rose'],
    base: fragrance.base_notes || ['Sandalwood', 'Musk'],
  };

  return (
    <div className="fragrance-detail-page">
      <div className="detail-container">
        {/* Back Button */}
        <button className="back-button" onClick={() => router.back()}>
          ← Back
        </button>

        {/* Header Section */}
        <div className="detail-header" ref={sectionRef}>
          <div className="fragrance-image-section">
            <div className="fragrance-image-large">🧴</div>
            <button
              className="wishlist-btn-large"
              onClick={() => addToWishlist(fragrance.id || params.id)}
              title="Add to wishlist"
            >
              ♡ Add to Wishlist
            </button>
          </div>

          <div className="fragrance-info-section">
            <div className="fragrance-header-info">
              <h1 className="fragrance-detail-title">{fragrance.name}</h1>
              <p className="fragrance-detail-brand">{fragrance.brand}</p>
              <p className="fragrance-year">{fragrance.year || 'Classic Edition'}</p>
            </div>

            <div className="fragrance-metrics">
              <div className="metric-block">
                <span className="metric-label">Rating</span>
                <div className="metric-value">
                  <span className="stars">
                    {'⭐'.repeat(Math.floor(fragrance.rating || 4))}
                  </span>
                  <span className="rating-count">
                    ({fragrance.review_count || 342} reviews)
                  </span>
                </div>
              </div>

              <div className="metric-block">
                <span className="metric-label">Match Score</span>
                <div className="metric-value">{fragrance.match_score || 87}%</div>
              </div>

              <div className="metric-block">
                <span className="metric-label">Longevity</span>
                <div className="metric-value">{fragrance.longevity || '8-10 hrs'}</div>
              </div>
            </div>

            <p className="fragrance-description">
              {fragrance.description ||
                'A sophisticated fragrance with a complex blend of notes that unfolds on the skin over time.'}
            </p>

            <div className="action-buttons-detail">
              <button
                className="btn-primary-detail"
                onClick={() => {
                  addToWishlist(fragrance.id || params.id);
                  alert('Added to wishlist!');
                }}
              >
                Add to Collection
              </button>
              <button
                className="btn-secondary-detail"
                onClick={() => router.push('/recommendations')}
              >
                See Similar
              </button>
            </div>
          </div>
        </div>

        {/* Note Pyramid Section */}
        <div className="note-pyramid-section">
          <h2 className="section-title">Fragrance Notes</h2>
          <div className="pyramid-container">
            <div className="pyramid-level base-level">
              <div className="level-label">Base Notes</div>
              <div className="notes-list">
                {notePyramid.base.map((note: string, idx: number) => (
                  <div key={idx} className="note-item base">
                    {note}
                  </div>
                ))}
              </div>
            </div>

            <div className="pyramid-level middle-level">
              <div className="level-label">Heart Notes</div>
              <div className="notes-list">
                {notePyramid.middle.map((note: string, idx: number) => (
                  <div key={idx} className="note-item middle">
                    {note}
                  </div>
                ))}
              </div>
            </div>

            <div className="pyramid-level top-level">
              <div className="level-label">Top Notes</div>
              <div className="notes-list">
                {notePyramid.top.map((note: string, idx: number) => (
                  <div key={idx} className="note-item top">
                    {note}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Details Section */}
        <div className="details-section">
          <div className="detail-card">
            <h3>Fragrance Profile</h3>
            <ul className="detail-list">
              <li>
                <span className="label">Type:</span>
                <span className="value">{fragrance.fragrance_type || 'Eau de Parfum'}</span>
              </li>
              <li>
                <span className="label">Concentration:</span>
                <span className="value">{fragrance.concentration || '15-20%'}</span>
              </li>
              <li>
                <span className="label">Sillage:</span>
                <span className="value">{fragrance.sillage || 'Moderate'}</span>
              </li>
              <li>
                <span className="label">Release Year:</span>
                <span className="value">{fragrance.year || 'Classic'}</span>
              </li>
            </ul>
          </div>

          <div className="detail-card">
            <h3>Recommended For</h3>
            <p className="card-content">
              {fragrance.recommendation || 'Perfect for everyday wear. Versatile and timeless.'}
            </p>
          </div>

          <div className="detail-card">
            <h3>Occasions</h3>
            <div className="occasion-tags">
              <span className="tag">Daily Wear</span>
              <span className="tag">Evening</span>
              <span className="tag">Special Events</span>
            </div>
          </div>
        </div>

        {/* Reviews Section */}
        <div className="reviews-section">
          <h2 className="section-title">Community Reviews</h2>
          <div className="reviews-grid">
            {[1, 2, 3].map((idx) => (
              <div key={idx} className="review-card">
                <div className="review-header">
                  <span className="reviewer-avatar">👤</span>
                  <div className="reviewer-info">
                    <p className="reviewer-name">User {idx} </p>
                    <span className="review-rating">
                      {'⭐'.repeat(5 - (idx % 2))}
                    </span>
                  </div>
                </div>
                <p className="review-text">
                  "This fragrance is absolutely stunning. The opening is fresh and bright, and
                  it develops beautifully over the course of the day."
                </p>
                <span className="review-date">2 days ago</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="detail-footer">
          <button
            className="footer-btn-primary"
            onClick={() => router.push('/recommendations')}
          >
            Back to Recommendations
          </button>
          <button
            className="footer-btn-secondary"
            onClick={() => router.push('/fragrances')}
          >
            Explore All Fragrances
          </button>
        </div>
      </div>
    </div>
  );
}
