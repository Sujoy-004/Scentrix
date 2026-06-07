'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Heart,
  ArrowRight,
  RotateCcw,
  ShieldCheck,
  LogIn,
  UserPlus,
} from 'lucide-react';
import { useRecommendations } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { DiscoveryNeuralLoader } from '@/components/DiscoveryNeuralLoader';
import { FragranceCard } from '@/components/FragranceCard';
import StateIndicator from '@/components/StateIndicator';
import { getFragrancePalette } from '@/lib/quizTheme';
import './recommendations.css';

const springConfig = { type: 'spring' as const, stiffness: 300, damping: 30 };

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

interface FragranceRecommendation {
  id: string;
  name: string;
  brand: string;
  match_score?: number;
  top_notes?: string[];
  reason?: string;
}

const cardVariants = {
  hidden: { opacity: 0, y: 30, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring' as const, stiffness: 100, damping: 20 }
  }
};

export default function RecommendationsPage() {
  const router = useRouter();
  const { data: recommendations, isLoading, error, state, stateLabel } = useRecommendations() as { data: FragranceRecommendation[] | undefined, isLoading: boolean, error: any, state: number | null, stateLabel: string | null };
  const { addToWishlist, isAuthenticated, quizResponses } = useAppStore();
  const [mounted, setMounted] = useState(false);
  const [visibleCount, setVisibleCount] = useState(10);

  useEffect(() => {
    setMounted(true);
  }, []);

  // SSR guard — avoid hydration mismatch on localStorage-backed state
  if (!mounted) return null;

  // ── GATE removed: anonymous users with zero ratings see recommendations immediately ──
  // (The guest auth banner below invites them to save.)
  // ── Guest with quiz data → allow discovery, show action banner later ──
  // We no longer block the user here. They see their results immediately.

  // ── Authenticated: loading state ──────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <DiscoveryNeuralLoader />
      </div>
    );
  }

  // ── Authenticated: error or no results (Cold Start Handling) ─────────────────
  if (error || !recommendations?.length) {
    // If they have quiz data but the backend returned nothing, it's likely a sync delay
    const isColdStart = quizResponses.length > 0;

    return (
      <div className="recommendations-error-screen" style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#050505' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card"
          style={{ padding: '3.5rem', textAlign: 'center', maxWidth: '34rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(244,187,146,0.1)', borderRadius: '2rem' }}
        >
          <div style={{ width: '4rem', height: '4rem', border: '1px solid rgba(244,187,146,0.2)', borderRadius: '50%', margin: '0 auto 2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <RotateCcw style={{ color: '#f4bb92', opacity: 0.6 }} size={32} />
          </div>

          <h2 style={{ fontSize: '1.75rem', fontFamily: 'var(--font-display)', fontStyle: 'italic', color: '#fff', marginBottom: '1rem', letterSpacing: '-0.02em' }}>
            {error ? "Neural Link Failed" : isColdStart ? "Neural Synthesis in Progress" : "Neural Sync Required"}
          </h2>

          <p style={{ color: 'rgba(255,255,255,0.5)', marginBottom: '2.5rem', lineHeight: '1.7', fontSize: '0.95rem' }}>
            {error
              ? "Failed to load recommendations. Please try again."
              : isColdStart
                ? "Your profile is being mapped across our 24,000 scents. This usually takes a moment on your first visit."
                : "We couldn't detect your olfactory signature. Please complete the Discovery Protocol to begin."}
          </p>

          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            {isColdStart && (
              <button
                className="btn btn-outline"
                onClick={() => window.location.reload()}
                style={{ borderRadius: '100px', padding: '0.75rem 2rem', fontSize: '0.8rem', letterSpacing: '0.1em' }}
              >
                Verify Sync
              </button>
            )}
            <button
              className="btn btn-primary"
              onClick={() => router.push('/quiz')}
              style={{ borderRadius: '100px', padding: '0.75rem 2.5rem', fontSize: '0.8rem', letterSpacing: '0.1em' }}
            >
              {isColdStart ? "Recalibrate" : "Enter Protocol"} <ArrowRight size={18} />
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  const topMatches = recommendations.slice(0, visibleCount);
  const topFragrance = topMatches[0];
  const palette = getFragrancePalette(topFragrance);

  const ratingCount = quizResponses.length;

  const stateHeaderLabel: Record<number, { badge: string; title: string; subtitle: string }> = {
    0: {
      badge: 'Popular Picks',
      title: 'Popular Fragrances',
      subtitle: 'Browse top scents chosen by our community. Rate a few to get personalized recommendations.',
    },
    1: {
      badge: 'Protocol Results Complete',
      title: 'Your Aromatic Constellation',
      subtitle: 'Finely tuned matches based on your neural preferences and taste geography.',
    },
    2: {
      badge: 'Cold Start — Early Personalization',
      title: 'Blended Matches',
      subtitle: 'Blending your preferences with neural similarity to refine your profile.',
    },
    3: {
      badge: 'Warm — Hybrid Learning',
      title: 'Your Evolving Selection',
      subtitle: 'Feature-based scoring with neural exploration to discover new favorites.',
    },
    4: {
      badge: 'Mature — Diversity Optimized',
      title: 'Curated for Depth',
      subtitle: 'Diversity-optimized recommendations across the full olfactive spectrum.',
    },
  };

  const header = state !== null && state in stateHeaderLabel
    ? stateHeaderLabel[state]
    : ratingCount === 0
      ? stateHeaderLabel[0]
      : stateHeaderLabel[1];

  return (
    <motion.div
      className="recommendations-page"
      initial={{ '--quiz-accent': '#f4bb92', '--quiz-soft': '#8b5e3c', '--quiz-glow': '#e4c285' } as any}
      animate={{
        '--quiz-accent': palette.accent,
        '--quiz-soft': palette.softSecondary,
        '--quiz-glow': palette.glow,
        '--color-primary': palette.accent,
        '--color-primary-container': palette.softSecondary,
        '--color-on-primary': palette.ink,
      } as any}
      transition={{ duration: 0.8, ease: 'easeInOut' }}
    >
      <div className="container mx-auto px-6">

        {/* Guest Auth Invitation Banner */}
        {!isAuthenticated && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="guest-auth-banner-elite"
          >
            <div className="flex items-center gap-4">
              <div className="banner-icon-pillar">
                <Sparkles size={16} className="text-primary" />
              </div>
              <div className="flex-1">
                <h4 className="text-[0.7rem] uppercase tracking-widest font-bold text-white mb-0.5">Guest Discovery Session</h4>
                <p className="text-[0.6rem] text-white/50 leading-tight">{ratingCount === 0 ? "Your session is temporary. Sign up to save your favorites." : "Your neural profile is temporary. Sign up to save these matches to your lifetime library."}</p>
              </div>
              <div className="flex gap-2">
                <Link href="/auth/register">
                  <button className="btn btn-primary px-8">Create Profile to Save</button>
                </Link>
              </div>
            </div>
          </motion.div>
        )}

        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="recommendations-header"
        >
          <div style={{ color: 'var(--color-primary)', fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: '1rem' }}>{header.badge}</div>
          <h1 className="font-display italic text-white mb-4">{header.title}</h1>
          <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.9rem', maxWidth: '30rem', margin: '0 auto' }}>
            {header.subtitle}
          </p>
        </motion.header>

        <StateIndicator state={state} stateLabel={stateLabel} ratingCount={ratingCount} />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="recommendations-stats-elite"
        >
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontFamily: 'var(--font-display)', color: '#fff' }}>{topMatches.length}</div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 700 }}>{ratingCount === 0 ? "Scents" : "Matches"}</div>
          </div>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="recommendations-grid-elite"
        >
          {topMatches.map((fragrance, index) => (
            <FragranceCard 
              key={fragrance.id || index}
              frag={fragrance}
              index={index}
              showMatch={ratingCount > 0}
            />
          ))}
        </motion.div>

        {visibleCount < recommendations.length && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center mt-12 pb-8"
          >
            <motion.button
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              className="btn btn-outline border-primary/30 text-primary px-12 py-4 text-xs tracking-[0.3em] font-bold"
              onClick={() => setVisibleCount((prev) => prev + 10)}
            >
              Show More Recommendations <ArrowRight className="ml-2" size={16} />
            </motion.button>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
