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
  const [rating, setRating] = useState<number | null>(5.0); 
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  const {
    addQuizResponse,
    clearQuizResponses,
    isAuthenticated,
    adaptiveQuiz,
    initializeAdaptiveQuiz,
    resetAdaptiveQuiz,
  } = useAppStore();

  const submitRatingMutation = useSubmitRating();
  const adaptiveSession = useAdaptiveQuizSession();
  const [fallbackFragrances, setFallbackFragrances] = useState<QuizCard[]>([]);

  // 3D TILT LOGIC
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(mouseY, [-300, 300], [10, -10]);
  const rotateY = useTransform(mouseX, [-300, 300], [-10, 10]);

  const fragrances = adaptiveQuiz.questionQueue.length > 0
    ? adaptiveQuiz.questionQueue
    : fallbackFragrances;

  // Swipe logic
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-10, 10]);
  const opacity = useTransform(x, [-200, -150, 0, 150, 200], [0, 1, 1, 1, 0]);

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const centerX = rect.left + width / 2;
    const centerY = rect.top + height / 2;
    mouseX.set(e.clientX - centerX);
    mouseY.set(e.clientY - centerY);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  useEffect(() => {
    let active = true;
    const loadCatalogFallback = async () => {
      try {
        const page = await api.getFragranceCatalog(100, 0);
        const mapped = (page?.items?.map((item: FragranceCatalogItem) => ({
          fragrance_id: item.id,
          name: item.name,
          brand: item.brand,
          top_notes: item.top_notes || [],
          accords: item.accords || [],
          family: item.family
        })) || []).sort(() => Math.random() - 0.5);
        
        if (active && mapped.length > 0) {
          setFallbackFragrances(mapped.slice(0, 12));
        }
      } catch (err) {
        if (active) setCatalogError('Neural link failed.');
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
      clearQuizResponses(); // Full Neural Purge for clean guest recommendations
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
        // Fallback for non-authed sessions
      } finally {
        if (active) setTimeout(() => setIsBootstrapping(false), 1200);
      }
    };
    void bootstrapAdaptiveQuiz();
    return () => { active = false; };
  }, []);

  const handleNext = async (val?: number) => {
    const finalRating = val ?? rating;
    if (finalRating === null || isTransitioning || fragrances.length === 0) return;

    setIsTransitioning(true);
    const currentFragrance = fragrances[currentFragranceIndex];

    try {
      addQuizResponse({ 
        fragrance_id: currentFragrance.fragrance_id, 
        rating: finalRating,
        top_notes: currentFragrance.top_notes,
        accords: currentFragrance.accords,
        name: currentFragrance.name,
        brand: currentFragrance.brand
      });
      if (isAuthenticated) {
        submitRatingMutation.mutate({ fragranceId: currentFragrance.fragrance_id, rating: finalRating });
      }

      if (currentFragranceIndex < fragrances.length - 1) {
        setCurrentFragranceIndex(prev => prev + 1);
        setRating(5.0);
        x.set(0);
      } else {
        router.push('/recommendations');
      }
    } finally {
      setIsTransitioning(false);
    }
  };

  if (isBootstrapping) return <DiscoveryNeuralLoader />;

  const currentFragrance = fragrances[currentFragranceIndex];
  if (!currentFragrance) return <div className="quiz-empty-state">Neural link lost. Refreshing...</div>;

  const palette = getFragrancePalette(currentFragrance);
  const progress = ((currentFragranceIndex + 1) / fragrances.length) * 100;

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
      } as any}
    >
      <div className="quiz-background-fixed" />
      
      <div className="quiz-container">
        <motion.header 
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="quiz-meta-header"
        >
          <div className="progress-indicator">
            <span className="step-count">Protocol {currentFragranceIndex + 1} / {fragrances.length}</span>
            <div className="progress-bar-wrap">
              <motion.div 
                className="progress-bar-fill"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
          </div>
        </motion.header>

        <AnimatePresence mode="wait">
          <motion.div
            key={currentFragrance.fragrance_id}
            initial={{ scale: 0.9, opacity: 0, y: 30 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 1.1, opacity: 0, y: -30 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="quiz-card-elite"
            style={{ x, rotate, opacity, rotateX, rotateY, perspective: 1000 }}
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            onDragEnd={(_, info) => {
              if (info.offset.x > 150) handleNext();
              else if (info.offset.x < -150) setCurrentFragranceIndex(prev => Math.min(prev + 1, fragrances.length - 1));
            }}
          >
            <div className="quiz-card-glass-pillar" />
            
            <div className="quiz-card-visual">
              <motion.div 
                animate={{ y: [0, -12, 0], rotate: [0, 5, 0] }}
                transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                className="visual-icon-nexus"
              >
                <Sparkles size={48} strokeWidth={1} />
              </motion.div>
              
              <div className="visual-details">
                <h2 className="frag-name-title italic">
                  {currentFragrance.accords.slice(0, 2).map((a, i) => (
                    <span key={a}>
                      {a}{i === 0 && currentFragrance.accords.length > 1 ? " & " : ""}
                    </span>
                  ))}
                  <span className="block text-[0.8rem] opacity-50 tracking-widest mt-2">Neural Profile {currentFragranceIndex + 1}</span>
                </h2>
              </div>

              {/* LIVE NEURAL GRAPHING COMPONENT */}
              <div className="quiz-live-graph-wrap">
                <NeuralGraph rating={rating || 5} />
              </div>
            </div>

            <div className="quiz-rating-interaction">
              <p className="interaction-label">Olfactory Signature</p>
              
              <div className="notes-capsules-nexus mb-10">
                {currentFragrance.top_notes.slice(0, 5).map(note => (
                  <motion.span 
                    key={note} 
                    className="note-capsule"
                    whileHover={{ scale: 1.1, backgroundColor: "var(--quiz-accent)", color: "#000", borderColor: "transparent" }}
                    whileTap={{ scale: 0.95 }}
                  >
                    {note}
                  </motion.span>
                ))}
              </div>
              
              <div className="rating-slider-nexus">
                <input 
                  type="range" 
                  min="1" max="10" step="0.1"
                  value={rating ?? 5}
                  onChange={(e) => setRating(parseFloat(e.target.value))}
                  className="elite-rating-range"
                />
                
                <div className="rating-readout">
                  <motion.span 
                    key={rating}
                    initial={{ y: 10, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    className="rating-value-h-f"
                  >
                    {rating ? rating.toFixed(1) : "5.0"}
                  </motion.span>
                  <span className="rating-total-h-f">/ 10</span>
                </div>
              </div>
            </div>

            <div className="quiz-card-actions">
              <button 
                onClick={() => setCurrentFragranceIndex(prev => Math.min(prev + 1, fragrances.length - 1))}
                className="quiz-action-btn skip"
              >
                Skip 
              </button>
              <motion.button 
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleNext()}
                disabled={rating === null || isTransitioning}
                className="quiz-action-btn confirm"
              >
                {isTransitioning ? "Synthesizing..." : "Confirm Rating"}
              </motion.button>
            </div>
          </motion.div>
        </AnimatePresence>

        <motion.footer 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="quiz-footer-meta"
        >
          <div className="meta-badge">
            <AlertCircle size={14} />
            <span>AI NEURAL SYNTHESIS ACTIVE</span>
          </div>
        </motion.footer>
      </div>
    </motion.div>
  );
}

function NeuralGraph({ rating }: { rating: number }) {
  const nodeCount = 6;
  const radius = 40;
  const centerX = 50;
  const centerY = 50;

  // Generate nodes in a circle
  const nodes = Array.from({ length: nodeCount }).map((_, i) => {
    const angle = (i * 2 * Math.PI) / nodeCount;
    // Nodes move outward as the rating increases
    const offset = (rating / 10) * 10; 
    return {
      x: centerX + (radius + offset) * Math.cos(angle),
      y: centerY + (radius + offset) * Math.sin(angle),
    };
  });

  // Calculate the "Core" path based on rating
  const coreRadius = 15 + (rating * 1.5);
  const pathD = Array.from({ length: nodeCount }).map((_, i) => {
    const angle = (i * 2 * Math.PI) / nodeCount;
    const px = centerX + coreRadius * Math.cos(angle);
    const py = centerY + coreRadius * Math.sin(angle);
    return `${i === 0 ? "M" : "L"} ${px} ${py}`;
  }).join(" ") + " Z";

  return (
    <div className="neural-nexus-container">
      <svg viewBox="0 0 100 100" className="neural-nexus-svg">
        <defs>
          <radialGradient id="neuralGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--quiz-accent)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="var(--quiz-accent)" stopOpacity="0" />
          </radialGradient>
        </defs>
        
        {/* NEURAL AURA */}
        <motion.circle 
          cx="50" cy="50"
          fill="url(#neuralGlow)"
          initial={{ r: 40, opacity: 0.3 }}
          animate={{ r: [40, 45, 40], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 4, repeat: Infinity }}
        />

        {/* CONNECTIONS (WEBS) */}
        {nodes.map((n, i) => (
          <motion.line 
            key={`line-${i}`}
            x1="50" y1="50"
            x2={n.x} y2={n.y}
            stroke="var(--quiz-accent)"
            strokeWidth="0.2"
            opacity="0.2"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
          />
        ))}

        {/* MORPHING FLAVOR CORE */}
        <motion.path 
          d={pathD}
          fill="var(--quiz-accent)"
          fillOpacity={0.1 + (rating / 100)}
          stroke="var(--quiz-accent)"
          strokeWidth="0.8"
          animate={{ scale: [1, 1.02, 1] }}
          transition={{ 
            d: { type: "spring", stiffness: 300, damping: 30 },
            scale: { duration: 2, repeat: Infinity, ease: "easeInOut" }
          }}
        />

        {/* DISCOVERY NODES */}
        {nodes.map((n, i) => (
          <motion.circle 
            key={`node-${i}`}
            cx={n.x} cy={n.y}
            fill="var(--quiz-accent)"
            initial={{ scale: 0, r: 1.5 }}
            animate={{ scale: 1 }}
            transition={{ delay: i * 0.1 }}
          />
        ))}
      </svg>
    </div>
  );
}

