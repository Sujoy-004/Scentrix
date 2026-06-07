'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { Sparkles, AlertCircle, ChevronRight } from 'lucide-react';
import { useAppStore } from '@/stores/app-store';
import { useAdaptiveQuizSession } from '@/lib/hooks';
import { api, VALID_IDS } from '@/lib/api';
import { getFragrancePalette } from '@/lib/quizTheme';
import { DiscoveryNeuralLoader } from '@/components/DiscoveryNeuralLoader';
import { buildLearningSummary } from '@/lib/reason-engine';
import posthog from 'posthog-js';
import '@/app/quiz/quiz.css';

type QuizPhase = 'rating' | 'extension-prompt' | 'loading' | 'success';

export default function StandardQuiz() {
  const router = useRouter();
  const store = useAppStore();
  const adaptiveSession = useAdaptiveQuizSession();

  const [currentFragranceIndex, setCurrentFragranceIndex] = useState(0);
  const [rating, setRating] = useState<number>(5.0);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  const [quizPhase, setQuizPhase] = useState<QuizPhase>('rating');
  const [extensionQuestionsCount, setExtensionQuestionsCount] = useState(0);
  const [finalError, setFinalError] = useState<string | null>(null);
  const [sessionResult, setSessionResult] = useState<{
    totalRated: number;
    confidenceScore: number;
    confidenceBand: string | null;
  } | null>(null);

  // 3D TILT LOGIC
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(mouseY, [-300, 300], [10, -10]);
  const rotateY = useTransform(mouseX, [-300, 300], [-10, 10]);

  const fragrances = store.adaptiveQuiz.questionQueue || [];

  useEffect(() => {
    let active = true;
    const bootstrapAdaptiveQuiz = async () => {
      try {
        const response = await adaptiveSession.startSession.mutateAsync({
          seed_count: 8,
          candidate_pool_size: 250,
          filters: { exclude_seen: true },
        });
        if (active) {
          store.initializeAdaptiveQuiz({
            sessionId: response.data.session_id,
            seedQuestions: response.data.seed_questions,
            rules: response.data.rules,
          });
        }
      } catch (error) {
        setCatalogError("Neural uplink unstable. Using atmospheric fallback.");
      } finally {
        if (active) setTimeout(() => setIsBootstrapping(false), 1200);
      }
    };
    bootstrapAdaptiveQuiz();
    return () => { active = false; };
  }, []);

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    mouseX.set(e.clientX - (rect.left + rect.width / 2));
    mouseY.set(e.clientY - (rect.top + rect.height / 2));
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  const handleNext = async (val: number = rating) => {
    if (isTransitioning || quizPhase !== 'rating') return;
    setIsTransitioning(true);

    const currentFragrance = fragrances[currentFragranceIndex];
    if (currentFragrance) {
      store.addQuizResponse({ ...currentFragrance, rating: val });

      const isCore = store.adaptiveQuiz.phase === 'core';
      store.markAdaptiveAnswer(isCore);

      if (store.adaptiveQuiz.sessionId) {
        api.submitQuizResponse(store.adaptiveQuiz.sessionId, {
          fragrance_id: currentFragrance.fragrance_id,
          rating_1_to_10: val,
          source: 'standard_quiz'
        }).catch((e) => {
          setFinalError('Some responses could not be saved to server, but they are stored locally.');
        });
      }
    }

    if (currentFragranceIndex < fragrances.length - 1) {
      setCurrentFragranceIndex(prev => prev + 1);
      setRating(5.0);
    } else {
      await checkExtension();
    }

    setTimeout(() => setIsTransitioning(false), 600);
  };

  const handleNeutral = () => handleNext(5.0);

  const checkExtension = async () => {
    if (!store.adaptiveQuiz.sessionId) {
      await finalizeSession();
      return;
    }

    try {
      const response = await api.evaluateQuizSession(
        store.adaptiveQuiz.sessionId,
        { force: false }
      );
      const evalData = response.data;

      store.setAdaptiveConfidence({
        confidenceScore: evalData.confidence_score,
        confidenceBand: evalData.confidence_band as 'high' | 'medium' | 'low' | null,
        extensionTarget: evalData.additional_questions_target,
        stopReason: evalData.stop_reason,
      });

      if (evalData.extension_required && evalData.additional_questions_target > 0) {
        setExtensionQuestionsCount(evalData.additional_questions_target);
        setQuizPhase('extension-prompt');
        return;
      }
    } catch (e) {
      // Evaluation failed — proceed to finalize
    }

    await finalizeSession();
  };

  const handleExtensionAccept = async () => {
    setQuizPhase('rating');
    setIsTransitioning(true);

    try {
      const response = await api.getNextQuizQuestions(
        store.adaptiveQuiz.sessionId!,
        extensionQuestionsCount
      );
      const questions = response.data?.questions || [];
      if (questions.length > 0) {
        store.appendAdaptiveQuestions(questions);
        store.setAdaptivePhase('extension');
        setCurrentFragranceIndex(prev => prev + 1);
        setRating(5.0);
      } else {
        await finalizeSession();
      }
    } catch (e) {
      await finalizeSession();
    }

    setIsTransitioning(false);
  };

  const handleExtensionDecline = async () => {
    await finalizeSession();
  };

  const finalizeSession = async () => {
    setQuizPhase('loading');
    setFinalError(null);

    const sessionId = store.adaptiveQuiz.sessionId;
    if (!sessionId) {
      const computed = computeAccordConfidence();
      store.setQuizConfidence(computed);
      setSessionResult({ totalRated: store.quizResponses.length, confidenceScore: 0, confidenceBand: 'low' });
      setQuizPhase('success');
      return;
    }

    let confidenceScore = 0;
    let confidenceBand: 'high' | 'medium' | 'low' | null = 'low';

    try {
      const evalResponse = await api.evaluateQuizSession(sessionId, { force: true });
      const evalData = evalResponse.data;
      confidenceScore = evalData.confidence_score;
      confidenceBand = evalData.confidence_band as 'high' | 'medium' | 'low' | null;
      store.setAdaptiveConfidence({
        confidenceScore,
        confidenceBand,
        extensionTarget: 0,
        stopReason: evalData.stop_reason,
      });
    } catch (e) {
      setFinalError('Profile evaluation encountered an issue, but your responses are saved.');
    }

    try {
      await api.guestFinalizeQuizSession(sessionId);
    } catch (e) {
      setFinalError(prev =>
        prev
          ? prev + ' Some data may not have synced. Your local data is preserved.'
          : 'Finalization encountered an issue, but your local data is preserved.'
      );
    }

    const computed = computeAccordConfidence();
    store.setQuizConfidence(computed);

    setSessionResult({ totalRated: store.quizResponses.length, confidenceScore, confidenceBand });
    setQuizPhase('success');
  };

  const computeAccordConfidence = (): Record<string, number> => {
    const accordScores: Record<string, number[]> = {};
    for (const response of store.quizResponses) {
      const weight = response.rating / 10;
      for (const accord of (response.accords || [])) {
        if (!accordScores[accord]) accordScores[accord] = [];
        accordScores[accord].push(weight);
      }
    }
    const computed: Record<string, number> = {};
    for (const [accord, scores] of Object.entries(accordScores)) {
      computed[accord.toLowerCase()] =
        scores.reduce((a, b) => a + b, 0) / scores.length;
    }
    return computed;
  };

  const handleGoToRecommendations = () => {
    router.push('/recommendations');
  };

  // ── Loading Phase ──────────────────────────────────────────
  if (quizPhase === 'loading') {
    return (
      <div className="quiz-page">
        <div className="quiz-background-fixed" />
        <div className="quiz-container">
          <motion.div
            className="phase-overlay"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="neural-spinner">
              <div className="spinner-ring" />
              <div className="spinner-ring spinner-ring-inner" />
            </div>
            <h2 className="phase-title">Synthesizing Your Neural Profile</h2>
            <p className="phase-subtitle">
              Mapping your preferences across our scent library...
            </p>
            {finalError && (
              <div className="phase-error">
                <AlertCircle size={14} />
                <span>{finalError}</span>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    );
  }

  // ── Success Phase ──────────────────────────────────────────
  if (quizPhase === 'success') {
    return (
      <div className="quiz-page">
        <div className="quiz-background-fixed" />
        <div className="quiz-container">
          <motion.div
            className="phase-overlay success-phase"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="success-icon">✦</div>
            <h2 className="phase-title">Discovery Protocol Complete</h2>
            <p className="phase-subtitle">
              Your olfactory profile has been mapped.
            </p>

            <div className="success-stats">
              <div className="success-stat">
                <span className="success-stat-value">{sessionResult?.totalRated || 0}</span>
                <span className="success-stat-label">Scents Rated</span>
              </div>
              <div className="success-stat-divider" />
              <div className="success-stat">
                <span className="success-stat-value" style={{ fontSize: '1.2rem' }}>
                  {(sessionResult?.confidenceScore ?? 0) >= 0.72 ? 'High' :
                   (sessionResult?.confidenceScore ?? 0) >= 0.58 ? 'Medium' : 'Building'}
                </span>
                <span className="success-stat-label">Profile Confidence</span>
              </div>
            </div>

            {(() => {
              const learning = buildLearningSummary(store.quizResponses);
              return learning.highlights.length > 0 ? (
                <div style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: '1rem',
                  padding: '1.25rem 1.5rem',
                  marginTop: '1.5rem',
                  textAlign: 'left',
                  maxWidth: '28rem',
                }}>
                  <p style={{ fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: '0.75rem' }}>Your Learning Profile</p>
                  {learning.highlights.map((h, i) => (
                    <p key={i} style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.6, marginBottom: '0.25rem' }}>• {h}</p>
                  ))}
                </div>
              ) : null;
            })()}

            {finalError && (
              <div className="phase-error" style={{ marginTop: '1.5rem' }}>
                <AlertCircle size={14} />
                <span>{finalError}</span>
              </div>
            )}

            <motion.button
              className="btn-quiz-primary success-cta"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleGoToRecommendations}
            >
              View Your Recommendations <ChevronRight size={18} style={{ marginLeft: '0.5rem' }} />
            </motion.button>
          </motion.div>
        </div>
      </div>
    );
  }

  // ── Bootstrap Phase ────────────────────────────────────────
  if (isBootstrapping) return <DiscoveryNeuralLoader />;

  const currentFragrance = fragrances[currentFragranceIndex];

  // ── Extension Prompt Phase ─────────────────────────────────
  if (quizPhase === 'extension-prompt') {
    return (
      <motion.div
        className="quiz-page"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          '--quiz-glow': 'rgba(244, 187, 146, 0.1)',
          '--quiz-accent': '#f4bb92',
          '--quiz-from': '#0a0a0a',
          '--quiz-to': '#050505',
          '--quiz-ink': '#ffffff',
          '--beam1': 'rgba(244, 187, 146, 0.15)',
          '--beam2': 'rgba(139, 94, 60, 0.1)',
          '--beam3': 'rgba(228, 194, 133, 0.05)',
        } as React.CSSProperties}
      >
        <div className="quiz-background-fixed" />
        <div className="quiz-container">
          <motion.div
            className="extension-prompt-card"
            initial={{ opacity: 0, y: 30, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="extension-prompt-glow" />
            <div className="extension-prompt-content">
              <div className="extension-prompt-badge">NEURAL REFINEMENT</div>
              <h2 className="extension-prompt-title">
                Refine Your Profile?
              </h2>
              <p className="extension-prompt-desc">
                Your current confidence is{' '}
                <strong>
                  {store.adaptiveQuiz.confidenceBand === 'low' ? 'low' : 'medium'}
                </strong>
                . Rate{' '}
                <strong>{extensionQuestionsCount} more</strong> scents to
                improve your match precision.
              </p>
              <div className="extension-prompt-actions">
                <button
                  className="btn-quiz-meta extension-decline"
                  onClick={handleExtensionDecline}
                >
                  See Results
                </button>
                <motion.button
                  className="btn-quiz-primary extension-accept"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  style={{
                    background: 'linear-gradient(135deg, #f4bb92, #d4956a)',
                    color: '#000',
                    boxShadow: '0 10px 40px rgba(244, 187, 146, 0.4)',
                  }}
                  onClick={handleExtensionAccept}
                >
                  Continue Rating
                </motion.button>
              </div>
            </div>
          </motion.div>

          <footer className="quiz-footer-meta">
            <div className="meta-badge">
              <Sparkles size={10} />
              <span>Adaptive Confidence Engine</span>
            </div>
          </footer>
        </div>
      </motion.div>
    );
  }

  if (!currentFragrance) return <div className="quiz-empty-state">Neural link lost. Refreshing...</div>;

  // ── Rating Phase ───────────────────────────────────────────
  const palette = getFragrancePalette(currentFragrance);
  const progressPercentage = ((currentFragranceIndex + 1) / (fragrances.length || 1)) * 100;
  const btnGradColors = palette.colors || ['#A66336', '#A66336', '#A66336'];

  return (
    <motion.div
      className="quiz-page"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        '--quiz-glow': palette.glow,
        '--quiz-accent': palette.accent,
        '--quiz-from': palette.pageFrom,
        '--quiz-to': palette.pageTo,
        '--quiz-ink': palette.ink,
        '--beam1': palette.beamRaw1,
        '--beam2': palette.beamRaw2,
        '--beam3': palette.beamRaw3,
      } as React.CSSProperties}
    >
      <div className="quiz-background-fixed" />

      <div className="quiz-container">
        <header className="quiz-meta-header">
          <div className="progress-indicator">
            <span className="step-count">
              {store.adaptiveQuiz.phase === 'extension' ? 'Refinement' : 'Discovery'}: {currentFragranceIndex + 1} / {fragrances.length}
            </span>
            <div className="progress-bar-wrap">
              <motion.div
                className="progress-bar-fill"
                animate={{ width: `${progressPercentage}%` }}
                transition={{ duration: 0.8 }}
                style={{ backgroundColor: palette.accent }}
              />
            </div>
          </div>
        </header>

        <AnimatePresence mode="wait">
          <motion.div
            key={currentFragrance.fragrance_id}
            className="quiz-card"
            style={{
              rotateX,
              rotateY,
              transformStyle: 'preserve-3d'
            }}
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: -20, filter: 'blur(15px)' }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >

            <section className="quiz-card-visual">
              <div className="frag-brand-label">
                {(currentFragrance.brand && currentFragrance.brand.toLowerCase() !== 'none')
                  ? currentFragrance.brand
                  : "Artisan Selection"}
              </div>
              <h2 className="frag-name-title" style={{
                fontSize: currentFragrance.name.length > 25 ? '1.5rem' : '2.25rem',
                lineHeight: 1.2
              }}>
                {currentFragrance.name}
              </h2>

              <div className="notes-capsules-nexus">
                {currentFragrance.top_notes?.slice(0, 3).map((note, idx) => (
                  <span key={idx} className="note-capsule">{note}</span>
                ))}
                {currentFragrance.accords?.slice(0, 3).map((accord, idx) => (
                  <span key={`acc-${idx}`} className="note-capsule" style={{ opacity: 0.3, fontSize: '0.6rem' }}>{accord}</span>
                ))}
              </div>
            </section>

            <section className="quiz-rating-interaction">
              <div className="interaction-label">How does this profile resonate?</div>
              <div className="rating-slider-nexus">
                <div className="rating-readout">
                  <span className="rating-value-h-f">{rating.toFixed(1)}</span>
                  <span className="rating-total-h-f">/ 10</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="0.1"
                  value={rating}
                  onChange={(e) => setRating(parseFloat(e.target.value))}
                  className="elite-rating-range"
                  style={{ '--quiz-accent': palette.accent } as any}
                />
              </div>
            </section>

            <footer className="quiz-controls-nexus">
              <button className="btn-quiz-meta" onClick={handleNeutral}>Neutral</button>
              <motion.button
                  key="confirm"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleNext()}
                  className="btn-quiz-primary"
                  style={{ 
                    background: `linear-gradient(135deg, ${palette.accent}, ${palette.accent}dd)`,
                    color: '#000',
                    boxShadow: `0 10px 40px ${palette.accent}66`
                  }}
                >
                  Confirm Dimension
                </motion.button>
            </footer>
          </motion.div>
        </AnimatePresence>

        <footer className="quiz-footer-meta">
          <div className="meta-badge">
            <Sparkles size={10} />
            <span>Neural Engine Active</span>
          </div>
        </footer>
      </div>

      {catalogError && (
        <div className="quiz-toast warning">
          <AlertCircle size={18} />
          <span>{catalogError}</span>
        </div>
      )}
    </motion.div>
  );
}
