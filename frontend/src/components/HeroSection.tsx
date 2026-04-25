'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  Sparkles, 
  ArrowRight, 
  Search, 
  Zap, 
  Users, 
  Database, 
  CheckCircle2 
} from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.3
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring' as const, stiffness: 50, damping: 20 }
  }
};

export function HeroSection() {
  const router = useRouter();

  return (
    <section className="hero-section constellation-bg min-h-screen flex items-center justify-center pt-20 overflow-hidden">
      <div className="hero-gradient" aria-hidden="true" />

      <motion.div 
        className="hero-container container relative z-10"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: false }}
      >
        <div className="hero-content max-w-6xl mx-auto">
          {/* Eyebrow */}
          <motion.div 
            variants={itemVariants}
            className="hero-eyebrow flex items-center justify-center gap-3 mb-8"
          >
            <motion.div
              animate={{ opacity: [0.4, 1, 0.4], scale: [1, 1.1, 1] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="w-2 h-2 rounded-full bg-primary glow-amber"
            />
            <span className="tracking-[0.4em] uppercase font-bold text-[0.65rem] text-primary/80 glow-amber">
              Neural Sommelier Protocol v2.0-REWIRED
            </span>
          </motion.div>

          {/* Cascading headline */}
          <motion.h1 
            variants={itemVariants}
            className="hero-title mb-10 text-center"
          >
            <span className="hero-title-main block mb-2 italic">Molecular Artistry.</span>
            <span className="hero-title-sub glow-amber-strong block text-primary">Neural Instinct.</span>
          </motion.h1>

          {/* Subtitle */}
          <motion.div 
            variants={itemVariants}
            className="hero-subtitle mb-16 max-w-2xl mx-auto px-4"
          >
            <p className="text-xl text-white/70 leading-relaxed font-light">
              Aethera translates molecular data into evocative, cinematic experiences. 
              Discover the <span className="text-primary italic font-medium">scent DNA</span> that defines your dimension.
            </p>
          </motion.div>

          {/* CTA Buttons */}
          <motion.div 
            variants={itemVariants}
            className="hero-buttons flex flex-wrap items-center justify-center gap-6"
          >
            <motion.button
              whileHover={{ scale: 1.05, y: -4 }}
              whileTap={{ scale: 0.95 }}
              className="btn btn-primary px-10 py-5 text-sm"
              onClick={() => router.push('/quiz')}
            >
              Start Discovery <ArrowRight className="ml-2" size={18} />
            </motion.button>
            
            <motion.button
              whileHover={{ scale: 1.05, y: -4 }}
              whileTap={{ scale: 0.95 }}
              className="btn btn-outline px-10 py-5 text-sm"
              onClick={() => router.push('/fragrances')}
            >
              Browse Library <Search className="ml-2" size={18} />
            </motion.button>
          </motion.div>

          {/* Trust Indicators */}
          <motion.div 
            variants={itemVariants}
            className="trust-indicators"
          >
            <StatItem icon={<Database size={20} />} value="5,130+" label="Elite Scents" />
            <StatItem icon={<Zap size={20} />} value="91.5%" label="Match Accuracy" />
            <StatItem icon={<Users size={20} />} value="50K+" label="Critics & Collectors" />
          </motion.div>
        </div>
      </motion.div>

      {/* Scroll hint */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 1 }}
        className="scroll-hint absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <span className="text-[0.6rem] uppercase tracking-[0.3em] font-bold text-white/30">Scroll to descend</span>
        <motion.div 
          animate={{ height: [40, 60, 40] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="w-px bg-gradient-to-b from-primary/40 to-transparent" 
        />
      </motion.div>
    </section>
  );
}

function StatItem({ icon, value, label }: { icon: React.ReactNode, value: string, label: string }) {
  return (
    <div className="indicator">
      <div className="stat-item-icon">{icon}</div>
      <span className="indicator-value">{value}</span>
      <span className="indicator-label">{label}</span>
    </div>
  );
}
