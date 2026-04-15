'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { 
  Sparkles, 
  ArrowRight, 
  ChevronRight, 
  RotateCcw, 
  AlertCircle,
  CheckCircle2,
  Trophy
} from 'lucide-react';
import { useAppStore } from '@/stores/app-store';
import { useAdaptiveQuizSession, useSubmitRating } from '@/lib/hooks';
import { api, type FragranceCatalogItem } from '@/lib/api';
import { getFragrancePalette } from '@/lib/quizTheme';
import { DiscoveryNeuralLoader } from '@/components/DiscoveryNeuralLoader';
import '@/app/onboarding/quiz/quiz.css';

type QuizCard = {
  fragrance_id: string;
  name: string;
  brand: string;
  top_notes: string[];
  accords: string[];
  family?: string;
};

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export default function StandardQuiz() {
  const router = useRouter();
  const [currentFragranceIndex, setCurrentFragranceIndex] = useState(0);
  const [rating, setRating] = useState<number>(5.0); 
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  const store = useAppStore();

  const submitRatingMutation = useSubmitRating();
  const adaptiveSession = useAdaptiveQuizSession();
  const [fallbackFragrances, setFallbackFragrances] = useState<QuizCard[]>([]);

  // 3D TILT LOGIC
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(mouseY, [-300, 300], [10, -10]);
  const rotateY = useTransform(mouseX, [-300, 300], [-10, 10]);

  const fragrances = store.adaptiveQuiz.questionQueue.length > 0
    ? store.adaptiveQuiz.questionQueue
    : fallbackFragrances;

  const x = useMotionValue(0);

  useEffect(() => {
    let active = true;
    const bootstrapAdaptiveQuiz = async () => {
      try {
        const response = await adaptiveSession.startSession.mutateAsync({
          seed_count: 8,
          candidate_pool_size: 200,
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

  const handleNext = async () => {
    if (rating === null) return;
    if (isTransitioning) return;

    setIsTransitioning(true);

    const currentFragrance = fragrances[currentFragranceIndex];
    if (currentFragrance) {
      const finalRating = rating;

      // 1. Local Commit
      store.addQuizResponse({
        fragrance_id: currentFragrance.fragrance_id,
        rating: finalRating,
        name: currentFragrance.name,
        brand: currentFragrance.brand,
        top_notes: currentFragrance.top_notes,
        accords: currentFragrance.accords
      });

      // 2. Global Sync
      if (store.adaptiveQuiz.sessionId) {
        try {
          await api.submitQuizResponse(store.adaptiveQuiz.sessionId, {
            fragrance_id: currentFragrance.fragrance_id,
            rating_1_to_10: finalRating,
            source: 'standard_quiz'
          });
          store.markAdaptiveAnswer(store.adaptiveQuiz.phase === 'core');
        } catch (e) {
          console.warn("Neural Sync lag:", e);
        }
      }
    }

    // 3. Navigation
    if (currentFragranceIndex < fragrances.length - 1) {
      setCurrentFragranceIndex(prev => prev + 1);
      setRating(5.0);
      x.set(0);
    } else {
      if (store.adaptiveQuiz.sessionId) {
        try {
          const evalResult = await api.evaluateQuizSession(store.adaptiveQuiz.sessionId, { force: false });
          
          store.setAdaptiveConfidence({
            confidenceScore: evalResult.confidence_score,
            confidenceBand: evalResult.confidence_band as any,
            extensionTarget: evalResult.additional_questions_target,
            stopReason: evalResult.stop_reason
          });

          if (evalResult.extension_required && evalResult.additional_questions_target > 0) {
            const nextBatch = await api.getNextQuizQuestions(store.adaptiveQuiz.sessionId, evalResult.additional_questions_target);
            store.appendAdaptiveQuestions(nextBatch.questions.map((q: any) => ({
              fragrance_id: q.fragrance_id,
              name: q.name,
              brand: q.brand,
              top_notes: q.top_notes,
              accords: q.accords,
            })));
            
            setCurrentFragranceIndex(prev => prev + 1);
            setRating(5.0);
            x.set(0);
          } else {
            await api.finalizeQuizSession(store.adaptiveQuiz.sessionId);
            router.push('/recommendations');
          }
        } catch (error) {
          console.error("Neural Evaluation failed:", error);
          router.push('/recommendations');
        }
      } else {
        router.push('/recommendations');
      }
    }

    setTimeout(() => setIsTransitioning(false), 600);
  };

  if (isBootstrapping) return <DiscoveryNeuralLoader />;

  const currentFragrance = fragrances[currentFragranceIndex];
  if (!currentFragrance) return <div className="quiz-empty-state">Neural link lost. Refreshing...</div>;

  const palette = getFragrancePalette(currentFragrance);
  const progressPercentage = ((currentFragranceIndex + 1) / fragrances.length) * 100;

  return (
    <motion.div 
      className="quiz-page"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        '--quiz-soft': palette.soft,
        '--quiz-glow': palette.glow,
        '--quiz-accent': palette.accent,
        '--quiz-from': palette.pageFrom,
        '--quiz-to': palette.pageTo,
        '--quiz-ink': palette.ink,
        '--color-primary': palette.accent,
        '--color-primary-container': palette.soft,
        '--color-primary-hover': palette.glow,
        '--color-accent': palette.accent,
      } as React.CSSProperties}
    >
      <div className="quiz-background-fixed" />

      <div className="quiz-container">
        {/* Progress Header */}
        <header className="quiz-meta-header">
          <div className="progress-indicator">
            <span className="step-count">Question {currentFragranceIndex + 1} of {fragrances.length}</span>
            <div className="progress-bar-wrap">
              <motion.div 
                className="progress-bar-fill"
                initial={{ width: 0 }}
                animate={{ width: `${progressPercentage}%` }}
                transition={{ duration: 0.8, ease: "circOut" }}
              />
            </div>
          </div>
        </header>

        {/* Main Content Card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentFragrance.fragrance_id}
            className="quiz-card-elite"
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -30, scale: 0.95, filter: 'blur(10px)' }}
            transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
            style={{ rotateX, rotateY, transformStyle: 'preserve-3d' }}
          >
            <div className="quiz-card-glass-pillar" />
            
            <section className="quiz-card-visual">
              <div className="frag-brand-label">{currentFragrance.brand || "Artisan Selection"}</div>
              <h2 className="frag-name-title">{currentFragrance.name}</h2>
              
              <div className="notes-capsules-nexus">
                {currentFragrance.top_notes?.slice(0, 3).map((note, idx) => (
                  <span key={idx} className="note-capsule">{note}</span>
                ))}
                {currentFragrance.accords?.slice(0, 3).map((accord, idx) => (
                  <span key={`acc-${idx}`} className="note-capsule" style={{ opacity: 0.4 }}>{accord}</span>
                ))}
              </div>
            </section>

            <section className="quiz-rating-interaction">
              <div className="interaction-label">How does this olfactive profile resonate?</div>
              
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
                />
                
                <div className="flex justify-between w-full opacity-30 text-[10px] uppercase tracking-widest mt-2 px-2">
                  <span>Avoid</span>
                  <span>Signature</span>
                </div>
              </div>
            </section>

            <footer className="quiz-card-actions">
              <button 
                className="quiz-action-btn skip"
                onClick={() => setRating(5.0)}
              >
                Neutral
              </button>
              <button 
                className="quiz-action-btn confirm"
                disabled={isTransitioning}
                onClick={handleNext}
              >
                Confirm Dimension
              </button>
            </footer>
          </motion.div>
        </AnimatePresence>

        <footer className="quiz-footer-meta">
          <div className="meta-badge">
            <Sparkles size={10} />
            <span>Neural Engine Synchronized</span>
          </div>
        </footer>
      </div>

      {catalogError && (
        <motion.div 
          className="quiz-toast warning"
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
        >
          <AlertCircle size={18} />
          <span>{catalogError}</span>
        </motion.div>
      )}
    </motion.div>
  );
}
