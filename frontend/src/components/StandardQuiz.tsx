'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { Sparkles, AlertCircle } from 'lucide-react';
import { useAppStore } from '@/stores/app-store';
import { useAdaptiveQuizSession } from '@/lib/hooks';
import { api } from '@/lib/api';
import { getFragrancePalette } from '@/lib/quizTheme';
import { DiscoveryNeuralLoader } from '@/components/DiscoveryNeuralLoader';
import '@/app/quiz/quiz.css';

export default function StandardQuiz() {
  const router = useRouter();
  const store = useAppStore();
  const adaptiveSession = useAdaptiveQuizSession();

  const [currentFragranceIndex, setCurrentFragranceIndex] = useState(0);
  const [rating, setRating] = useState<number>(5.0);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);

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
            sessionId: response.session_id,
            seedQuestions: response.seed_questions,
            rules: response.rules,
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
    if (isTransitioning) return;
    setIsTransitioning(true);

    const currentFragrance = fragrances[currentFragranceIndex];
    if (currentFragrance) {
      store.addQuizResponse({ ...currentFragrance, rating: val });

      if (store.adaptiveQuiz.sessionId) {
        api.submitQuizResponse(store.adaptiveQuiz.sessionId, {
          fragrance_id: currentFragrance.fragrance_id,
          rating_1_to_10: val,
          source: 'standard_quiz'
        }).catch(console.warn);
      }
    }

    if (currentFragranceIndex < fragrances.length - 1) {
      setCurrentFragranceIndex(prev => prev + 1);
      setRating(5.0);
    } else {
      finalizeSession();
    }

    setTimeout(() => setIsTransitioning(false), 600);
  };

  const handleNeutral = () => handleNext(5.0);

  const finalizeSession = async () => {
    if (store.adaptiveQuiz.sessionId) {
      // Circuit Breaker: enforce a 5s timeout on neural engine calls.
      // If it hangs, we guarantee the user reaches recommendations.
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Neural circuit breaker: evaluation timeout')), 5000)
      );
      try {
        const evalResult = await Promise.race([
          api.evaluateQuizSession(store.adaptiveQuiz.sessionId, { force: false }),
          timeoutPromise,
        ]);
        if (!evalResult.extension_required) {
          // Best-effort finalize — don't block navigation on this
          api.finalizeQuizSession(store.adaptiveQuiz.sessionId).catch(() => {});
        }
      } catch (err) {
        // Breaker tripped or error — log and proceed, never trap the user
        console.warn('[Circuit Breaker] Neural evaluation bypassed:', err);
      }
    }
    router.push('/recommendations');
  };


  if (isBootstrapping) return <DiscoveryNeuralLoader />;

  const currentFragrance = fragrances[currentFragranceIndex];
  if (!currentFragrance) return <div className="quiz-empty-state">Neural link lost. Refreshing...</div>;

  const palette = getFragrancePalette(currentFragrance);
  const progressPercentage = ((currentFragranceIndex + 1) / (fragrances.length || 1)) * 100;

  // Ensure we have 3 colors for the gradient
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
            <span className="step-count">Discovery: {currentFragranceIndex + 1} / {fragrances.length}</span>
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
              <button
                className="btn-quiz-primary"
                onClick={() => handleNext()}
                style={{
                  background: `linear-gradient(135deg, ${btnGradColors[0]}, ${btnGradColors[1]}, ${btnGradColors[2]})`,
                  boxShadow: `0 10px 30px -10px ${btnGradColors[0]}88`
                }}
              >
                Confirm Dimension
              </button>
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
