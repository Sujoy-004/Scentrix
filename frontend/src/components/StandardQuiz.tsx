'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import { useAdaptiveQuizSession, useSubmitRating } from '@/lib/hooks';
import { api, type FragranceCatalogItem } from '@/lib/api';
import { getFragrancePalette } from '@/lib/quizTheme';
import '@/app/onboarding/quiz/quiz.css';

type QuizCard = {
  fragrance_id: string;
  name: string;
  brand: string;
  top_notes: string[];
  accords: string[];
};

type ApiErrorLike = {
  response?: {
    status?: number;
    data?: {
      detail?: unknown;
    };
  };
};

function getHttpStatus(error: unknown): number | null {
  const parsed = error as ApiErrorLike;
  const status = parsed?.response?.status;
  return typeof status === 'number' ? status : null;
}

function mapCatalogToCards(items: FragranceCatalogItem[]): QuizCard[] {
  return items
    .filter((item) => typeof item.id === 'string' && item.id.trim().length > 0)
    .map((item) => ({
      fragrance_id: item.id,
      name: item.name || 'Unknown',
      brand: item.brand || 'Unknown',
      top_notes: Array.isArray(item.top_notes)
        ? item.top_notes.map((note) => String(note))
        : [],
      accords: Array.isArray(item.accords)
        ? item.accords.map((value) => String(value))
        : [],
    }));
}

export default function StandardQuiz() {
  const router = useRouter();

  const [currentFragranceIndex, setCurrentFragranceIndex] = useState(0);
  const [rating, setRating] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [adaptiveEnabled, setAdaptiveEnabled] = useState(true);
  const [adaptiveWarning, setAdaptiveWarning] = useState<string | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [authApiEnabled, setAuthApiEnabled] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const hasDowngradedAuthRef = useRef(false);

  const {
    addQuizResponse,
    clearQuizResponses,
    isAuthenticated,
    adaptiveQuiz,
    initializeAdaptiveQuiz,
    appendAdaptiveQuestions,
    markAdaptiveAnswer,
    setAdaptivePhase,
    setAdaptiveConfidence,
    resetAdaptiveQuiz,
  } = useAppStore();

  const submitRatingMutation = useSubmitRating();
  const adaptiveSession = useAdaptiveQuizSession();
  const [fallbackFragrances, setFallbackFragrances] = useState<QuizCard[]>([]);
  const canUseAuthedApis = isAuthenticated && authApiEnabled;

  const downgradeToGuestMode = (warning: string) => {
    if (hasDowngradedAuthRef.current) {
      return;
    }

    hasDowngradedAuthRef.current = true;
    setAuthApiEnabled(false);
    setAdaptiveEnabled(false);
    setAdaptiveWarning(warning);

    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_id');
    }
    if (typeof document !== 'undefined') {
      document.cookie = 'auth_token=; Max-Age=0; path=/; SameSite=Lax';
    }

    useAppStore.setState({ authToken: null, isAuthenticated: false, userId: null });
  };

  const fragrances = adaptiveQuiz.questionQueue.length > 0
    ? adaptiveQuiz.questionQueue
    : fallbackFragrances;
  const sessionId = adaptiveQuiz.sessionId;

  useEffect(() => {
    let active = true;

    const loadCatalogFallback = async () => {
      try {
        const page = await api.getFragranceCatalog(8, 0);
        const mapped = mapCatalogToCards(Array.isArray(page?.items) ? page.items : []);
        if (active && mapped.length > 0) {
          setFallbackFragrances(mapped);
          setCatalogError(null);
        } else if (active) {
          setCatalogError('No fragrances available. Please try again later.');
        }
      } catch {
        if (active) {
          setCatalogError('Failed to load fragrances. Please check your connection and try again.');
        }
      }
    };

    void loadCatalogFallback();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    const bootstrapAdaptiveQuiz = async () => {
      setIsBootstrapping(true);
      setAdaptiveEnabled(true);
      setAdaptiveWarning(null);
      setErrorMsg(null);
      setCurrentFragranceIndex(0);
      setRating(null);
      clearQuizResponses();
      resetAdaptiveQuiz();

      if (!canUseAuthedApis) {
        if (active) {
          setAdaptiveEnabled(false);
          setIsBootstrapping(false);
        }
        return;
      }

      try {
        const response = await adaptiveSession.startSession.mutateAsync({
          seed_count: 8,
          candidate_pool_size: 200,
          filters: { exclude_seen: true },
        });

        if (!active) {
          return;
        }

        initializeAdaptiveQuiz({
          sessionId: response.session_id,
          seedQuestions: response.seed_questions,
          rules: response.rules,
        });
        setAdaptivePhase('core');
      } catch (error) {
        const status = getHttpStatus(error);
        if (!active) {
          return;
        }

        if (status === 401) {
          downgradeToGuestMode('Your session expired. Continuing with the standard quiz flow.');
        }

        setAdaptiveEnabled(false);
        if (status !== 401) {
          setAdaptiveWarning('Adaptive quiz is temporarily unavailable. Continuing with the standard quiz flow.');
        }
      } finally {
        if (active) {
          setIsBootstrapping(false);
        }
      }
    };

    void bootstrapAdaptiveQuiz();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (fragrances.length === 0) {
      return;
    }
    if (currentFragranceIndex >= fragrances.length) {
      setCurrentFragranceIndex(fragrances.length - 1);
    }
  }, [currentFragranceIndex, fragrances.length]);

  const hasAnyQuizResponse = () => useAppStore.getState().quizResponses.length > 0;

  const finalizeQuiz = async () => {
    if (!hasAnyQuizResponse()) {
      setErrorMsg('Please rate at least one fragrance before getting recommendations.');
      return;
    }

    if (!adaptiveEnabled || !sessionId) {
      router.push('/recommendations');
      return;
    }

    try {
      const evaluation = await adaptiveSession.evaluateSession.mutateAsync({
        sessionId,
        payload: { force: false },
      });

      setAdaptiveConfidence({
        confidenceScore: evaluation.confidence_score,
        confidenceBand: evaluation.confidence_band,
        extensionTarget: evaluation.additional_questions_target,
        stopReason: evaluation.stop_reason,
      });

      if (evaluation.extension_required && evaluation.additional_questions_target > 0) {
        const nextQuestions = await adaptiveSession.fetchNextQuestions.mutateAsync({
          sessionId,
          count: evaluation.additional_questions_target,
        });

        if (nextQuestions.questions.length > 0) {
          appendAdaptiveQuestions(nextQuestions.questions);
          setAdaptivePhase('extension');
          setCurrentFragranceIndex((index) => index + 1);
          setRating(null);
          return;
        }
      }

      setAdaptivePhase('final');
      router.push('/recommendations');
    } catch (error) {
      const status = getHttpStatus(error);
      if (status === 401) {
        downgradeToGuestMode('Your session expired. Continuing with your current quiz answers.');
      }
      setAdaptiveEnabled(false);
      if (status !== 401) {
        setAdaptiveWarning('Adaptive confidence checks are temporarily unavailable. Continuing with your current answers.');
      }
      setAdaptivePhase('final');
      router.push('/recommendations');
    }
  };

  const isLoading = isBootstrapping || (fallbackFragrances.length === 0 && !catalogError);
  const isBusy =
    isBootstrapping ||
    isTransitioning ||
    adaptiveSession.submitResponse.isPending ||
    adaptiveSession.evaluateSession.isPending ||
    adaptiveSession.fetchNextQuestions.isPending;

  const handleRating = (value: number | null) => {
    if (value === null || Number.isNaN(value)) {
      setRating(null);
      return;
    }
    const safe = Math.min(10, Math.max(1, value));
    setRating(Number(safe.toFixed(1)));
  };

  const handleNext = async () => {
    if (isBusy) {
      return;
    }

    setErrorMsg(null);
    if (rating === null || fragrances.length === 0) {
      return;
    }

    const currentFragrance = fragrances[currentFragranceIndex];
    if (!currentFragrance) {
      return;
    }

    const isCorePhase = adaptiveQuiz.phase !== 'extension';

    setIsTransitioning(true);

    try {
      addQuizResponse({
        fragrance_id: currentFragrance.fragrance_id,
        rating,
      });

      if (canUseAuthedApis) {
        submitRatingMutation.mutate(
          { fragranceId: currentFragrance.fragrance_id, rating },
          {
            onError: (err) => {
              const status = getHttpStatus(err);
              if (status === 401) {
                downgradeToGuestMode('Your session expired. Continuing in guest mode.');
              }
            },
          }
        );
      }

      if (adaptiveEnabled && sessionId) {
        try {
          await adaptiveSession.submitResponse.mutateAsync({
            sessionId,
            payload: {
              fragrance_id: currentFragrance.fragrance_id,
              rating_1_to_10: rating,
              source: isCorePhase ? 'quiz_core' : 'quiz_extension',
            },
          });
          markAdaptiveAnswer(isCorePhase);
        } catch (error) {
          const status = getHttpStatus(error);
          if (status === 401) {
            downgradeToGuestMode('Your session expired. Continuing with your current quiz questions.');
          }
          setAdaptiveEnabled(false);
          if (status !== 401) {
            setAdaptiveWarning('Adaptive session sync failed. Continuing with your current quiz questions.');
          }
        }
      }

      if (currentFragranceIndex < fragrances.length - 1) {
        setCurrentFragranceIndex(currentFragranceIndex + 1);
        setRating(null);
      } else {
        await finalizeQuiz();
      }
    } finally {
      setIsTransitioning(false);
    }
  };

  const handleSkip = async () => {
    if (isBusy) {
      return;
    }

    setErrorMsg(null);

    if (currentFragranceIndex < fragrances.length - 1) {
      setCurrentFragranceIndex(currentFragranceIndex + 1);
      setRating(null);
    } else {
      setIsTransitioning(true);
      try {
        await finalizeQuiz();
      } finally {
        setIsTransitioning(false);
      }
    }
  };

  if (isLoading) {
    return <div className="quiz-loading">Loading fragrances...</div>;
  }

  if (catalogError) {
    return (
      <div className="quiz-loading" style={{ textAlign: 'center', padding: '2rem' }}>
        <p style={{ color: '#FF5A37', marginBottom: '1rem' }}>{catalogError}</p>
        <button
          onClick={() => window.location.reload()}
          className="quiz-btn"
          style={{ background: 'transparent', border: '1px solid #FF5A37', color: '#FF5A37', padding: '0.8rem 1.5rem', borderRadius: '8px', cursor: 'pointer' }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (fragrances.length === 0) {
    return <div className="quiz-loading">Loading fragrances...</div>;
  }

  const currentFragrance = fragrances[currentFragranceIndex] ?? fragrances[0];
  if (!currentFragrance) {
    return <div className="quiz-loading">Loading fragrances...</div>;
  }

  const progress = ((currentFragranceIndex + 1) / fragrances.length) * 100;
  const palette = getFragrancePalette(currentFragrance);
  const totalQuestions = fragrances.length;
  const progressLabel = `${progress.toFixed(0)}%`;

  return (
    <div
      className="quiz-page"
      style={{
        '--quiz-soft': palette.soft,
        '--quiz-soft-secondary': palette.softSecondary,
        '--quiz-border': palette.border,
        '--quiz-glow': palette.glow,
        '--quiz-accent': palette.accent,
        '--quiz-page-from': palette.pageFrom,
        '--quiz-page-to': palette.pageTo,
        '--quiz-beam': palette.beam,
        '--quiz-ink': palette.ink,
      } as any}
    >
      <div className="quiz-container">
        <div className="quiz-header" string="reveal">
          <h1>Discover Your Signature Scent</h1>
          <p>Rate your favorite fragrances to get personalized recommendations</p>
          {adaptiveWarning && (
            <p style={{ marginTop: '0.75rem', fontSize: '0.95rem', color: '#f6c08d' }}>
              {adaptiveWarning}
            </p>
          )}
        </div>

        <div className="quiz-progress-meta" string="reveal">
          <span className="quiz-progress-text">Progress</span>
          <strong className="quiz-progress-value">{progressLabel}</strong>
        </div>

        <div
          className="quiz-card"
          style={{
            '--quiz-soft': palette.soft,
            '--quiz-soft-secondary': palette.softSecondary,
            '--quiz-border': palette.border,
            '--quiz-glow': palette.glow,
            '--quiz-accent': palette.accent,
          } as any}
          string="impulse"
          string-continuous-push="false"
          string-position-strength="0.12"
          string-position-tension="0.1"
          string-position-friction="0.14"
          string-rotation-strength="0.08"
          string-rotation-tension="0.1"
          string-rotation-friction="0.14"
        >
          <div className="fragrance-preview">
            <div className="fragrance-emoji">🧴</div>
            <h2 className="fragrance-title">{currentFragrance.name}</h2>
            <p className="fragrance-brand">{currentFragrance.brand}</p>
          </div>

          <div className="rating-section" string="reveal" style={{ animationDelay: `0.2s` }}>
            <p className="rating-label">Give this fragrance a precise score</p>
            <div className="rating-field-wrap" string="impulse" string-continuous-push="false" string-position-strength="0.08">
              <label htmlFor="quiz-rating" className="rating-input-label">Your rating</label>
              <div className="rating-input-shell">
                <input
                  id="quiz-rating"
                  type="number"
                  inputMode="decimal"
                  min="1"
                  max="10"
                  step="0.1"
                  value={rating ?? ''}
                  onChange={(e) => {
                    const raw = e.target.value;
                    if (!raw) {
                      handleRating(null);
                      return;
                    }
                    handleRating(Number(raw));
                  }}
                  className="rating-input"
                  placeholder="7.8"
                  aria-label="Rate this fragrance from 1 to 10"
                />
                <span className="rating-suffix">/10</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                step="0.1"
                value={rating ?? 5.0}
                onChange={(e) => handleRating(Number(e.target.value))}
                className="rating-slider"
                aria-label="Adjust rating from 1 to 10"
              />
              <div className="rating-scale">
                <span>1.0</span>
                <span>5.5</span>
                <span>10.0</span>
              </div>
              <p className="rating-help">Range: 1.0 to 10.0. Decimals like 5.7 or 8.1 are supported.</p>
            </div>

            <div className="rating-quick-picks">
              {[1.0, 5.7, 8.1, 10.0].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  className={`rating-chip ${rating === preset ? 'active' : ''}`}
                  onClick={() => handleRating(preset)}
                >
                  {preset.toFixed(1)}
                </button>
              ))}
            </div>

            <div className="rating-display">
              {rating !== null ? rating.toFixed(1) : '--'} / 10
            </div>

            <div className="quiz-progress-footnote">
              Question {currentFragranceIndex + 1} of {totalQuestions}
            </div>
          </div>

          <div className="quiz-notes-preview" string="reveal" style={{ animationDelay: `0.4s` }}>
            <p className="notes-title">Top Notes:</p>
            <div className="notes-pills">
              {currentFragrance.top_notes?.map((note: string) => (
                <span key={note} className="note-pill">
                  {note}
                </span>
              ))}
            </div>
          </div>

          <div className="quiz-controls">
            <button
              className="quiz-btn quiz-btn-skip"
              onClick={handleSkip}
              disabled={isBusy}
            >
              Skip
            </button>
            <button
              className="quiz-btn quiz-btn-next-primary"
              onClick={handleNext}
              disabled={rating === null || isBusy}
              string="impulse"
              string-continuous-push="false"
              string-position-strength="0.07"
              string-position-tension="0.1"
              string-position-friction="0.12"
            >
              {isBusy
                ? 'Processing...'
                : currentFragranceIndex === fragrances.length - 1
                  ? 'Continue'
                  : 'Next Fragrance'}
            </button>
          </div>

          <div className="quiz-counter">
            {currentFragranceIndex + 1} of {fragrances.length}
          </div>

          {errorMsg && (
            <div className="quiz-error" style={{ color: '#FF5A37', marginTop: '1.5rem', textAlign: 'center' }}>
              <p style={{ fontWeight: 'bold' }}>{errorMsg}</p>
              <button
                onClick={() => {
                  setErrorMsg(null);
                  setCurrentFragranceIndex(0);
                  setRating(null);
                }}
                className="quiz-btn"
                style={{ marginTop: '1rem', background: 'transparent', border: '1px solid #FF5A37', color: '#FF5A37', width: '100%', padding: '0.8rem', borderRadius: '8px', cursor: 'pointer' }}
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
