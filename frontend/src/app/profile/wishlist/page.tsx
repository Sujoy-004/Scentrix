'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useWishlist, useRemoveFromWishlist } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import './wishlist.css';

export default function WishlistPage() {
  const router = useRouter();
  const { isAuthenticated } = useAppStore();
  const { data: wishlist = [], isLoading, error } = useWishlist();
  const removeFromWishlistMutation = useRemoveFromWishlist();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  const handleRemove = (wishlistId: string) => {
    if (confirm('Remove from wishlist?')) {
      removeFromWishlistMutation.mutate(wishlistId);
    }
  };

  return (
    <div className="wishlist-page">
      <div className="wishlist-container">
        {/* Header */}
        <div className="wishlist-header">
          <div>
            <h1>My Wishlist</h1>
            <p>Your saved fragrances</p>
          </div>
          <button
            className="back-to-home"
            onClick={() => router.push('/')}
          >
            ← Back to Home
          </button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="wishlist-loading">
            <div className="loading-spinner">
              <p>Loading wishlist...</p>
              <div className="spinner"></div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="wishlist-error">
            <h2>Unable to load wishlist</h2>
            <p>Please try again later.</p>
            <button
              className="error-button"
              onClick={() => router.push('/')}
            >
              Back to Home
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && wishlist.length === 0 && (
          <div className="wishlist-empty">
            <div className="empty-icon">💐</div>
            <h2>Your wishlist is empty</h2>
            <p>Start exploring fragrances and save your favorites!</p>
            <button
              className="cta-button"
              onClick={() => router.push('/fragrances')}
            >
              Browse Fragrances
            </button>
            <button
              className="secondary-button"
              onClick={() => router.push('/quiz')}
            >
              Take the Quiz
            </button>
          </div>
        )}

        {/* Wishlist Grid */}
        {!isLoading && !error && wishlist.length > 0 && (
          <div>
            <div className="wishlist-info">
              <p>{wishlist.length} fragrance{wishlist.length !== 1 ? 's' : ''} saved</p>
              <div className="wishlist-actions">
                <button
                  className="action-secondary"
                  onClick={() => alert('Share feature coming soon!')}
                >
                  Share Wishlist
                </button>
                <button
                  className="action-secondary"
                  onClick={() => alert('Export feature coming soon!')}
                >
                  Export as PDF
                </button>
              </div>
            </div>

            <div className="wishlist-grid">
              {wishlist.map((item: any) => (
                (() => {
                  const fragrance = item.fragrance ?? item;
                  return (
                <div key={item.id} className="wishlist-card">
                  <div className="wishlist-card-header">
                    <h3>{fragrance.name || item.fragrance_neo4j_id}</h3>
                    <button
                      className="remove-button"
                      onClick={() => handleRemove(item.id)}
                      disabled={removeFromWishlistMutation.isPending}
                    >
                      {removeFromWishlistMutation.isPending ? '...' : '✕'}
                    </button>
                  </div>

                  <div className="wishlist-card-info">
                    <p className="brand">{fragrance.brand || 'Saved fragrance'}</p>
                    <div className="card-details">
                      <span className="family">
                        {fragrance.family || 'N/A'}
                      </span>
                      <span className="rating">
                        ⭐ {fragrance.rating?.toFixed(1) || 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="wishlist-card-notes">
                    <p className="notes-label">Top Notes:</p>
                    <p className="notes-value">
                      {fragrance.top_notes?.join(', ') || item.notes || 'N/A'}
                    </p>
                  </div>

                  <div className="wishlist-card-actions">
                    <button
                      className="view-detail-button"
                      onClick={() =>
                        router.push(
                          `/fragrances/${fragrance.id || item.fragrance_neo4j_id}`
                        )
                      }
                    >
                      View Details
                    </button>
                    <button
                      className="add-to-cart-button"
                      onClick={() =>
                        alert('Shop integration coming soon!')
                      }
                    >
                      Shop Now
                    </button>
                  </div>

                  <div className="wishlist-card-meta">
                    <small>
                      Added{' '}
                      {item.added_at || item.created_at
                        ? new Date(
                            item.added_at || item.created_at
                          ).toLocaleDateString()
                        : 'recently'}
                    </small>
                  </div>
                </div>
                  );
                })()
              ))}
            </div>
          </div>
        )}

        {/* Footer CTA */}
        {!isLoading && !error && wishlist.length > 0 && (
          <div className="wishlist-footer">
            <button
              className="browse-more-button"
              onClick={() => router.push('/fragrances')}
            >
              ← Browse More Fragrances
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
