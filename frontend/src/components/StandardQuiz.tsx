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

  const fragrances = adaptiveQuiz.questionQueue.length > 0
    ? adaptiveQuiz.questionQueue
    : fallbackFragrances;
  const sessionId = adaptiveQuiz.sessionId;

  // Swipe logic
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-25, 25]);
  const opacity = useTransform(x, [-200, -150, 0, 150, 200], [0, 1, 1, 1, 0]);

  useEffect(() => {
    let active = true;
    const loadCatalogFallback = async () => {
      try {
        const page = await api.getFragranceCatalog(8, 0);
        const mapped = page?.items?.map(item => ({
          fragrance_id: item.id,
          name: item.name,
          brand: item.brand,
          top_notes: item.top_notes || [],
          accords: item.accords || [],
          family: item.family
        })) || [];
        if (active && mapped.length > 0) {
          setFallbackFragrances(mapped);
        }
      } catch (err) {
        if (active) setCatalogError('Failed to load library.');
      }
    };
    void loadCatalogFallback();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    const bootstrapAdaptiveQuiz = async () => {
      setIsBootstrapping(true);
      resetAdaptiveQuiz();
      if (!canUseAuthedApis) {
        if (active) setIsBootstrapping(false);
        return;
      }
      try {
        const response = await adaptiveSession.startSession.mutateAsync({
          seed_count: 8,
          candidate_pool_size: 200,
          filters: { exclude_seen: true },
        });
        if (active) {
          initializeAdaptiveQuiz({
            sessionId: response.session_id,
            seedQuestions: response.seed_questions,
            rules: response.rules,
          });
        }
      } catch (error) {
        if (active) setAdaptiveEnabled(false);
      } finally {
        if (active) setIsBootstrapping(false);
      }
    };
    void bootstrapAdaptiveQuiz();
    return () => { active = false; };
  }, [canUseAuthedApis]);

  const handleNext = async (val?: number) => {
    const finalRating = val ?? rating;
    if (finalRating === null || isTransitioning || fragrances.length === 0) return;

    setIsTransitioning(true);
    const currentFragrance = fragrances[currentFragranceIndex];

    try {
      addQuizResponse({ fragrance_id: currentFragrance.fragrance_id, rating: finalRating });
      
      if (canUseAuthedApis) {
        submitRatingMutation.mutate({ fragranceId: currentFragrance.fragrance_id, rating: finalRating });
      }

      if (currentFragranceIndex < fragrances.length - 1) {
        setCurrentFragranceIndex(prev => prev + 1);
        setRating(null);
        x.set(0);
      } else {
        router.push('/recommendations');
      }
    } finally {
      setIsTransitioning(false);
    }
  };

  if (isBootstrapping) return <div className="quiz-loading glass">Calibrating Senses...</div>;

  const currentFragrance = fragrances[currentFragranceIndex];
  if (!currentFragrance) return null;

  const palette = getFragrancePalette(currentFragrance);
  const progress = ((currentFragranceIndex + 1) / fragrances.length) * 100;

  return (
    <motion.div 
      className="quiz-page"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{
        '--quiz-soft': palette.soft,
        '--quiz-glow': palette.glow,
        '--quiz-accent': palette.accent,
        '--quiz-page-from': palette.pageFrom,
        '--quiz-page-to': palette.pageTo,
      } as any}
    >
      <div className="quiz-container max-w-2xl mx-auto px-6 pt-32">
        <motion.header 
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="text-center mb-12"
        >
          <h1 className="text-3xl font-display italic text-white mb-2">Discovery Protocol</h1>
          <p className="text-muted text-sm">Rating {currentFragranceIndex + 1} of {fragrances.length}</p>
          
          <div className="w-full h-1 bg-white/5 rounded-full mt-8 overflow-hidden">
            <motion.div 
              className="h-full bg-primary shadow-[0_0_8px_var(--color-primary)]"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={springConfig}
            />
          </div>
        </motion.header>

        <AnimatePresence mode="wait">
          <motion.div
            key={currentFragrance.fragrance_id}
            initial={{ x: 100, opacity: 0, rotate: 10 }}
            animate={{ x: 0, opacity: 1, rotate: 0 }}
            exit={{ x: -100, opacity: 0, rotate: -10 }}
            transition={springConfig}
            className="quiz-card-elite glass p-10 rounded-[2.5rem] relative"
            style={{ x, rotate, opacity }}
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            onDragEnd={(_, info) => {
              if (info.offset.x > 100 && rating !== null) handleNext();
              else if (info.offset.x < -100) setCurrentFragranceIndex(prev => Math.min(prev + 1, fragrances.length - 1));
            }}
          >
            <div className="text-center mb-10">
              <motion.div 
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="w-24 h-24 mx-auto mb-6 flex items-center justify-center bg-primary/10 rounded-full text-primary"
              >
                <Sparkles size={40} />
              </motion.div>
              <h2 className="text-2xl font-display italic text-white mb-1">{currentFragrance.name}</h2>
              <p className="text-primary text-xs uppercase tracking-widest font-bold">{currentFragrance.brand}</p>
            </div>

            <div className="space-y-8">
              <div className="rating-area">
                <div className="flex justify-between text-[0.65rem] uppercase tracking-tighter text-muted mb-4 px-2">
                  <span>Muted</span>
                  <span>Intense</span>
                </div>
                <input 
                  type="range" 
                  min="1" max="10" step="0.1"
                  value={rating ?? 5}
                  onChange={(e) => setRating(parseFloat(e.target.value))}
                  className="w-full h-2 bg-white/5 rounded-full appearance-none cursor-pointer accent-primary"
                />
                <div className="text-center mt-6">
                  <motion.span 
                    key={rating}
                    initial={{ scale: 1.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="text-4xl font-display italic text-gradient-amber"
                  >
                    {rating ? rating.toFixed(1) : "—"}
                  </motion.span>
                  <span className="text-muted ml-2">/ 10</span>
                </div>
              </div>

              <div className="border-t border-white/5 pt-8">
                <h4 className="text-[0.65rem] uppercase tracking-widest text-muted mb-4">Aromatic Profile</h4>
                <div className="flex flex-wrap gap-2">
                  {currentFragrance.top_notes.slice(0, 4).map(note => (
                    <span key={note} className="px-3 py-1 bg-white/5 rounded-full text-[0.65rem] text-white/70 border border-white/10 italic">
                      {note}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-4 mt-12">
              <button 
                onClick={() => setCurrentFragranceIndex(prev => Math.min(prev + 1, fragrances.length - 1))}
                className="flex-1 py-4 rounded-2xl bg-white/5 text-muted text-xs uppercase font-bold tracking-widest hover:bg-white/10 transition-colors"
              >
                Skip
              </button>
              <motion.button 
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleNext()}
                disabled={rating === null || isTransitioning}
                className="flex-[2] py-4 rounded-2xl bg-primary text-on-primary text-xs uppercase font-bold tracking-widest shadow-xl shadow-primary/20 disabled:opacity-50"
              >
                {isTransitioning ? "Analyzing..." : "Confirm Rating"}
              </motion.button>
            </div>
          </motion.div>
        </AnimatePresence>

        <motion.footer 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-12 text-center text-[0.65rem] text-muted flex items-center justify-center gap-2"
        >
          <AlertCircle size={12} />
          <span>Ratings directly influence your curated Neural Scent Graph</span>
        </motion.footer>
      </div>
    </motion.div>
  );
}
