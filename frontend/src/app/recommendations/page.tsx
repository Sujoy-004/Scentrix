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
  Star
} from 'lucide-react';
import { useRecommendations } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
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
  const { data: recommendations, isLoading, error } = useRecommendations();
  const { addToWishlist } = useAppStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  if (isLoading) {
    return (
      <div className="recommendations-loading min-h-screen">
        <motion.div 
          animate={{ 
            scale: [1, 1.2, 1],
            rotate: [0, 90, 180, 270, 360],
          }}
          transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
          className="loading-artifact"
          style={{ width: '8rem', height: '8rem', border: '1px solid rgba(244,187,146,0.2)', borderRadius: '50%', background: 'rgba(244,187,146,0.05)', position: 'relative' }}
        >
          <Sparkles style={{ position: 'absolute', inset: 0, margin: 'auto', color: '#f4bb92' }} size={40} />
        </motion.div>
        <p style={{ color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '0.3em', fontWeight: 'bold' }}>
          Synthesizing Neural Scent Graph...
        </p>
      </div>
    );
  }

  if (error || !recommendations?.length) {
    return (
      <div className="recommendations-error-screen" style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000' }}>
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-card"
          style={{ padding: '3rem', textAlign: 'center', maxWidth: '30rem' }}
        >
          <RotateCcw style={{ margin: '0 auto 1.5rem', color: 'rgba(244,187,146,0.5)' }} size={48} />
          <h2 style={{ fontSize: '1.5rem', fontFamily: 'var(--font-display)', fontStyle: 'italic', color: '#fff', marginBottom: '1rem' }}>Discovery Required</h2>
          <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '2rem', lineHeight: '1.6' }}>
            We haven't calibrated your profile yet. Complete the Discovery Protocol to generate your personalized scent landscape.
          </p>
          <button className="btn btn-primary" onClick={() => router.push('/onboarding/quiz')}>
            Enter Protocol <ArrowRight size={18} />
          </button>
        </motion.div>
      </div>
    );
  }

  const topMatches = recommendations.slice(0, 10);

  return (
    <div className="recommendations-page">
      <div className="container mx-auto px-6">
        
        <motion.header 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="recommendations-header"
        >
          <div style={{ color: '#f4bb92', fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: '1rem' }}>Protocol Results Complete</div>
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
            <div style={{ fontSize: '2rem', fontFamily: 'var(--font-display)', color: '#f4bb92' }}>98%</div>
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
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#f4bb92' }}>{fragrance.match_score || 85}%</span>
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
    </div>
  );
}
