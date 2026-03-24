'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import './history.css';

// Mock hook for quiz history - would be a real hook in production
const useQuizHistory = () => {
  return {
    data: [
      {
        id: 1,
        date: '2024-01-20',
        recommendationCount: 10,
        topMatch: 'Creed - Aventus',
        matchScore: 94,
      },
      {
        id: 2,
        date: '2024-01-15',
        recommendationCount: 10,
        topMatch: 'Tom Ford - Black Orchid',
        matchScore: 87,
      },
      {
        id: 3,
        date: '2024-01-10',
        recommendationCount: 10,
        topMatch: 'Dior - Sauvage',
        matchScore: 91,
      },
    ],
    isLoading: false,
    error: null,
  };
};

export default function QuizHistoryPage() {
  const router = useRouter();
  const { isAuthenticated } = useAppStore();
  const { data: history = [], isLoading, error } = useQuizHistory();

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
        {/* Header */}
        <div className="history-header">
          <div>
            <h1>Quiz History</h1>
            <p>Your past assessments and recommendations</p>
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
          <div className="history-loading">
            <div className="loading-spinner">
              <p>Loading history...</p>
              <div className="spinner"></div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="history-error">
            <h2>Unable to load history</h2>
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
        {!isLoading && !error && history.length === 0 && (
          <div className="history-empty">
            <div className="empty-icon">📋</div>
            <h2>No quiz history yet</h2>
            <p>Take the quiz to discover fragrances tailored to you!</p>
            <button
              className="cta-button"
              onClick={() => router.push('/onboarding/quiz')}
            >
              Take the Quiz
            </button>
          </div>
        )}

        {/* History Timeline */}
        {!isLoading && !error && history.length > 0 && (
          <div className="history-timeline">
            <div className="timeline-info">
              <p>{history.length} quiz{history.length !== 1 ? 'zes' : ''} completed</p>
            </div>

            {history.map((quiz: any, index: number) => (
              <div key={quiz.id} className="timeline-item">
                <div className="timeline-marker">
                  <div className="timeline-dot"></div>
                  {index < history.length - 1 && (
                    <div className="timeline-line"></div>
                  )}
                </div>

                <div className="timeline-content">
                  <div className="quiz-card">
                    <div className="quiz-header">
                      <h3>Quiz Assessment</h3>
                      <span className="quiz-date">
                        {new Date(quiz.date).toLocaleDateString('en-US', {
                          weekday: 'long',
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </span>
                    </div>

                    <div className="quiz-stats">
                      <div className="stat">
                        <span className="stat-label">Top Match</span>
                        <p className="stat-value">{quiz.topMatch}</p>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Match Score</span>
                        <p className="stat-value">{quiz.matchScore}%</p>
                      </div>
                      <div className="stat">
                        <span className="stat-label">Recommendations</span>
                        <p className="stat-value">
                          {quiz.recommendationCount}
                        </p>
                      </div>
                    </div>

                    <div className="match-progress">
                      <div
                        className="match-bar"
                        style={{
                          width: `${quiz.matchScore}%`,
                        }}
                      ></div>
                    </div>

                    <div className="quiz-actions">
                      <button
                        className="view-results"
                        onClick={() =>
                          router.push(
                            `/recommendations?quiz=${quiz.id}`
                          )
                        }
                      >
                        View Recommendations
                      </button>
                      <button
                        className="retake-quiz"
                        onClick={() => router.push('/onboarding/quiz')}
                      >
                        Retake Quiz
                      </button>
                      <button
                        className="delete-quiz"
                        onClick={() => {
                          if (
                            confirm(
                              'Delete this quiz from history?'
                            )
                          ) {
                            alert('Quiz deleted');
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer CTA */}
        {!isLoading && !error && history.length > 0 && (
          <div className="history-footer">
            <button
              className="take-new-quiz"
              onClick={() => router.push('/onboarding/quiz')}
            >
              Take a New Quiz
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
