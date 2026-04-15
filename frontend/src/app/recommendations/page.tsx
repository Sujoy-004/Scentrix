'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
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
  const { data: recommendations, isLoading, error } = useRecommendations() as { data: FragranceRecommendation[] | undefined, isLoading: boolean, error: any };
  const { addToWishlist, isAuthenticated, quizResponses } = useAppStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // SSR guard — avoid hydration mismatch on localStorage-backed state
  if (!mounted) return null;

  // ── GATE 1: Guest with no quiz data → send them to the quiz ─────────────
  if (!isAuthenticated && quizResponses.length === 0) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#050505' }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-card"
          style={{ padding: '3rem', textAlign: 'center', maxWidth: '30rem', border: '1px solid rgba(200,161,90,0.1)', borderRadius: '1.5rem', background: 'rgba(255,255,255,0.03)' }}
        >
          <Sparkles style={{ margin: '0 auto 1.5rem', color: 'rgba(200,161,90,0.5)' }} size={48} />
          <h2 style={{ fontSize: '1.5rem', fontFamily: 'var(--font-display)', fontStyle: 'italic', color: '#fff', marginBottom: '1rem' }}>
            Begin Your Discovery
          </h2>
          <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '2rem', lineHeight: '1.6' }}>
            Take the Discovery Protocol to calibrate your neural scent profile.
          </p>
          <button className="btn btn-primary" onClick={() => router.push('/onboarding/quiz')}>
            Enter Protocol <ArrowRight size={18} />
          </button>
        </motion.div>
      </div>
    );
  }

  // ── GATE 2: Guest with quiz data → show Login/Sign Up gate ──────────────
  if (!isAuthenticated && quizResponses.length > 0) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#050505', padding: '2rem' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          style={{ textAlign: 'center', maxWidth: '34rem' }}
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            style={{ width: '5rem', height: '5rem', border: '1px solid rgba(200,161,90,0.3)', borderRadius: '50%', margin: '0 auto 2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <Sparkles size={28} style={{ color: '#C8A15A' }} />
          </motion.div>

          <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.25em', textTransform: 'uppercase', color: 'rgba(200,161,90,0.7)', marginBottom: '1rem' }}>
            Neural Calibration Complete
          </div>
          <h1 style={{ fontSize: '2rem', fontFamily: 'var(--font-display)', fontStyle: 'italic', color: '#fff', marginBottom: '0.75rem', lineHeight: 1.2 }}>
            Your Aromatic Profile is Ready
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '0.9rem', lineHeight: 1.7, marginBottom: '2.5rem' }}>
            You rated <strong style={{ color: '#C8A15A' }}>{quizResponses.length}</strong> fragrances.
            Sign in or create a free account to unlock your personalized discovery landscape.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxWidth: '18rem', margin: '0 auto' }}>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push('/auth/register')}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '0.85rem 2rem', background: 'linear-gradient(135deg, rgba(200,161,90,0.9), rgba(90,42,27,0.8))', border: 'none', borderRadius: '100px', color: '#0a0806', fontWeight: 700, fontSize: '0.8rem', letterSpacing: '0.1em', textTransform: 'uppercase', cursor: 'pointer' }}
            >
              <UserPlus size={16} /> Create Free Account
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push('/auth/login')}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '0.85rem 2rem', background: 'transparent', border: '1px solid rgba(200,161,90,0.3)', borderRadius: '100px', color: 'rgba(255,255,255,0.8)', fontWeight: 600, fontSize: '0.8rem', letterSpacing: '0.08em', textTransform: 'uppercase', cursor: 'pointer' }}
            >
              <LogIn size={16} /> Sign In to Existing Account
            </motion.button>
          </div>

          <p style={{ marginTop: '2rem', fontSize: '0.65rem', color: 'rgba(255,255,255,0.25)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            <ShieldCheck size={10} style={{ display: 'inline', marginRight: '0.3rem', color: '#C8A15A' }} />
            Your quiz data stays local until you sign up. We never share it.
          </p>
        </motion.div>
      </div>
    );
  }

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
            {isColdStart ? "Neural Synthesis in Progress" : "Neural Sync Required"}
          </h2>
          
          <p style={{ color: 'rgba(255,255,255,0.5)', marginBottom: '2.5rem', lineHeight: '1.7', fontSize: '0.95rem' }}>
            {isColdStart 
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
              onClick={() => router.push('/onboarding/quiz')}
              style={{ borderRadius: '100px', padding: '0.75rem 2.5rem', fontSize: '0.8rem', letterSpacing: '0.1em' }}
            >
              {isColdStart ? "Recalibrate" : "Enter Protocol"} <ArrowRight size={18} />
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  const topMatches = recommendations.slice(0, 10);
  const topFragrance = topMatches[0];
  const palette = getFragrancePalette(topFragrance);

  const avgFidelity = topMatches.length > 0 
    ? Math.round(topMatches.reduce((acc, curr) => acc + (curr.match_score || 0), 0) / topMatches.length)
    : 0;

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
        
        <motion.header 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="recommendations-header"
        >
          <div style={{ color: 'var(--color-primary)', fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: '1rem' }}>Protocol Results Complete</div>
          <h1 className="font-display italic text-white mb-4">Your Aromatic Constellation</h1>
          <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.9rem', maxWidth: '30rem', margin: '0 auto' }}>
            Finely tuned matches based on your neural preferences and taste geography.
          </p>
        </motion.header>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="recommendations-stats-elite"
        >
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontFamily: 'var(--font-display)', color: '#fff' }}>{topMatches.length}</div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 700 }}>Matches</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontFamily: 'var(--font-display)', color: 'var(--color-primary)' }}>{avgFidelity}%</div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 700 }}>Fidelity</div>
          </div>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="recommendations-grid-elite"
        >
          {topMatches.map((fragrance, index) => (
            <motion.div 
              key={fragrance.id || index}
              variants={cardVariants}
              whileHover={{ y: -8 }}
              className="recommendation-card-elite"
            >
              <div style={{ position: 'absolute', top: '1.5rem', right: '1.5rem' }}>
                <button 
                  onClick={() => addToWishlist(fragrance.id)}
                  style={{ width: '2.5rem', height: '2.5rem', border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', borderRadius: '50%', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                  <Heart size={16} />
                </button>
              </div>

              <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
                <div style={{ fontSize: '5rem', position: 'absolute', top: '-1rem', left: '-1rem', fontFamily: 'var(--font-display)', fontStyle: 'italic', opacity: 0.05, color: '#fff' }}>
                  #{index + 1}
                </div>
                <h3 style={{ fontSize: '1.25rem', fontFamily: 'var(--font-display)', fontStyle: 'italic', color: '#fff', marginBottom: '0.25rem' }}>{fragrance.name}</h3>
                <p style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700, color: 'rgba(255,255,255,0.5)' }}>{fragrance.brand}</p>
              </div>

              <div className="match-score-elite">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', padding: '0 0.25rem' }}>
                  <span style={{ fontSize: '0.6rem', fontWeight: 700, color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>Neural Match</span>
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#f4bb92' }}>{fragrance.match_score}%</span>
                </div>
                <div className="score-track-elite">
                  <motion.div 
                    initial={{ width: 0 }}
                    whileInView={{ width: `${fragrance.match_score || 85}%` }}
                    transition={{ ...springConfig, delay: 0.5 }}
                    className="score-fill-elite"
                  />
                </div>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '2.5rem' }}>
                {fragrance.top_notes?.slice(0, 3).map((note: string) => (
                  <span key={note} style={{ fontSize: '0.6rem', padding: '0.25rem 0.75rem', borderRadius: '100px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)', textTransform: 'uppercase', fontWeight: 700 }}>
                    {note}
                  </span>
                ))}
              </div>

              <div className="card-actions-elite">
                <button 
                  onClick={() => router.push(`/fragrances/${fragrance.id}`)}
                  className="btn-details-elite"
                >
                  Details
                </button>
                <button 
                  onClick={() => router.push(`/fragrances/${fragrance.id}?view=similar`)}
                  className="btn-similar-elite"
                >
                  Similar
                </button>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <motion.div 
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          className="recommendations-footer-elite"
        >
          <div className="footer-actions-elite">
            <button className="btn btn-outline" onClick={() => router.push('/fragrances')}>
              Explore All
            </button>
            <button className="btn btn-primary" onClick={() => router.push('/onboarding/quiz')}>
              Recalibrate
            </button>
          </div>
          <p style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.15em', fontStyle: 'italic', color: 'rgba(255,255,255,0.4)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={12} style={{ color: '#f4bb92' }} /> Verified Neural Sync
          </p>
        </motion.div>
      </div>
    </motion.div>
  );
}
