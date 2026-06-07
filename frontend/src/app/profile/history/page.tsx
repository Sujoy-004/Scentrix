'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import { useQuizSummary } from '@/lib/hooks';
import './history.css';

export default function QuizHistoryPage() {
  const router = useRouter();
  const { isAuthenticated } = useAppStore();
  const { data: summary, isLoading, error } = useQuizSummary();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="history-page">
      <div className="history-container">
        <div className="history-header">
          <div>
            <h1>Last Quiz Summary</h1>
            <p>Your most recent fragrance assessment</p>
          </div>
          <button
            className="back-to-home"
            onClick={() => router.push('/')}
          >
            ← Back to Home
          </button>
        </div>

        {isLoading && (
          <div className="history-loading">
            <div className="loading-spinner">
              <p>Loading summary...</p>
              <div className="spinner"></div>
            </div>
          </div>
        )}

        {error && (
          <div className="history-error">
            <h2>Unable to load summary</h2>
            <p>Please try again later.</p>
            <button
              className="error-button"
              onClick={() => router.push('/')}
            >
              Back to Home
            </button>
          </div>
        )}

        {!isLoading && !error && (!summary || !summary.has_completed_quiz) && (
          <div className="history-empty">
            <div className="empty-icon">📋</div>
            <h2>No quiz completed yet</h2>
            <p>Take the quiz to discover fragrances tailored to you!</p>
            <button
              className="cta-button"
              onClick={() => router.push('/quiz')}
            >
              Take the Quiz
            </button>
          </div>
        )}

        {!isLoading && !error && summary?.has_completed_quiz && (
          <>
            <div className="summary-card">
              <div className="summary-header">
                <div className="summary-date-badge">
                  Completed on {new Date(summary.completed_at).toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </div>
              </div>

              <div className="summary-stats">
                <div className="summary-stat">
                  <span className="summary-stat-value">{summary.total_rated}</span>
                  <span className="summary-stat-label">Fragrances Rated</span>
                </div>
                <div className="summary-stat">
                  <span className="summary-stat-value">{summary.average_rating}</span>
                  <span className="summary-stat-label">Avg Rating (1-10)</span>
                </div>
                <div className="summary-stat">
                  <span className="summary-stat-value">{summary.average_normalized}</span>
                  <span className="summary-stat-label">Avg (0-5)</span>
                </div>
              </div>

              <div className="rating-distribution">
                <span className="distribution-label">Rating Distribution</span>
                <div className="distribution-bars">
                  <div className="distribution-bar-group">
                    <span className="bar-label">High</span>
                    <div className="distribution-bar-track">
                      <div
                        className="distribution-bar distribution-bar-high"
                        style={{
                          width: `${summary.total_rated > 0 ? (summary.rating_distribution.high / summary.total_rated) * 100 : 0}%`,
                        }}
                      ></div>
                    </div>
                    <span className="bar-count">{summary.rating_distribution.high}</span>
                  </div>
                  <div className="distribution-bar-group">
                    <span className="bar-label">Med</span>
                    <div className="distribution-bar-track">
                      <div
                        className="distribution-bar distribution-bar-medium"
                        style={{
                          width: `${summary.total_rated > 0 ? (summary.rating_distribution.medium / summary.total_rated) * 100 : 0}%`,
                        }}
                      ></div>
                    </div>
                    <span className="bar-count">{summary.rating_distribution.medium}</span>
                  </div>
                  <div className="distribution-bar-group">
                    <span className="bar-label">Low</span>
                    <div className="distribution-bar-track">
                      <div
                        className="distribution-bar distribution-bar-low"
                        style={{
                          width: `${summary.total_rated > 0 ? (summary.rating_distribution.low / summary.total_rated) * 100 : 0}%`,
                        }}
                      ></div>
                    </div>
                    <span className="bar-count">{summary.rating_distribution.low}</span>
                  </div>
                </div>
              </div>

              {summary.top_notes.length > 0 && (
                <div className="summary-tags">
                  <span className="tags-label">Top Notes</span>
                  <div className="tags-list">
                    {summary.top_notes.map((note: string) => (
                      <span key={note} className="tag">{note}</span>
                    ))}
                  </div>
                </div>
              )}

              {summary.top_accords.length > 0 && (
                <div className="summary-tags">
                  <span className="tags-label">Top Accords</span>
                  <div className="tags-list">
                    {summary.top_accords.map((accord: string) => (
                      <span key={accord} className="tag tag-accord">{accord}</span>
                    ))}
                  </div>
                </div>
              )}

              {summary.top_matches.length > 0 && (
                <div className="summary-matches">
                  <span className="matches-label">Top Matches</span>
                  <div className="matches-list">
                    {summary.top_matches.map((match: any) => (
                      <div key={match.id} className="match-item">
                        <div className="match-info">
                          <span className="match-name">{match.name}</span>
                          <span className="match-brand">{match.brand}</span>
                        </div>
                        <div className="match-score-badge">
                          {match.match_score}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="history-footer">
              <button
                className="take-new-quiz"
                onClick={() => router.push('/quiz')}
              >
                Retake Quiz
              </button>
              <button
                className="view-recommendations-btn"
                onClick={() => router.push('/recommendations')}
              >
                View Recommendations
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
