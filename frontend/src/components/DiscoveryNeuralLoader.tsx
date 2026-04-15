'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ScentrixLogo } from './ScentrixLogo';

interface DiscoveryLoaderProps {
  title?: string;
}

export function DiscoveryNeuralLoader({ title }: DiscoveryLoaderProps) {
  const [loreIndex, setLoreIndex] = useState(0);
  const [particles, setParticles] = useState<any[]>([]);
  const loadingFacts = [
    "Synthesizing 2.1M Graph Relationships...",
    "Decoding Animalic Musks...",
    "Decanting Rare Ouds...",
    "Mapping Olfactive Deserts...",
    "Isolating Ambergris Molecules...",
    "Calibrating Neural Sentiment...",
    "Waking the Digital Sommelier..."
  ];

  useEffect(() => {
    // Generate particles ONLY on client after mount
    const newParticles = [...Array(20)].map((_, i) => ({
      id: i,
      width: Math.random() * 4 + 1 + 'px',
      height: Math.random() * 4 + 1 + 'px',
      left: Math.random() * 100 + '%',
      top: Math.random() * 100 + '%',
      y: [0, -100 - Math.random() * 100],
      duration: 5 + Math.random() * 10,
      delay: Math.random() * 5
    }));
    setParticles(newParticles);

    const timer = setInterval(() => {
      setLoreIndex((prev) => (prev + 1) % loadingFacts.length);
    }, 2800);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="discovery-loader-premium" style={{
      '--quiz-accent': '#f4bb92',
      '--quiz-glow': 'rgba(244,187,146,0.2)',
      '--quiz-ink': '#f4bb92',
    } as any}>
      {/* Background Cinematic Particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none" suppressHydrationWarning>
        {particles.map((p) => (
          <motion.div 
            key={p.id}
            className="absolute bg-white/10 rounded-full"
            style={{
              width: p.width,
              height: p.height,
              left: p.left,
              top: p.top,
            }}
            animate={{ 
              y: p.y,
              opacity: [0, 0.4, 0],
              scale: [1, 1.5, 1]
            }}
            transition={{ 
              duration: p.duration, 
              repeat: Infinity, 
              ease: "linear",
              delay: p.delay 
            }}
          />
        ))}
      </div>

      <motion.div 
        className="loader-minimal-content relative z-10"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          gap: '3rem'
        }}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="relative">
          <motion.div 
            animate={{ scale: [1, 1.05, 1], opacity: [0.5, 0.8, 0.5] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          >
            <ScentrixLogo size={160} />
          </motion.div>
          {/* Orbital rings */}
          <div className="absolute inset-0 -m-8 border border-white/5 rounded-full animate-[spin_20s_linear_infinite]" />
          <div className="absolute inset-0 -m-16 border border-white/5 rounded-full animate-[spin_35s_linear_infinite_reverse]" />
        </div>
        
        <div className="glass-card p-8 rounded-[2rem] max-w-md w-full border-white/10 bg-black/40 backdrop-blur-3xl">
          <AnimatePresence mode="wait">
            <motion.div 
              key={loreIndex}
              className="mb-8"
              initial={{ opacity: 0, y: 10, filter: 'blur(4px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -10, filter: 'blur(4px)' }}
              transition={{ duration: 0.5 }}
            >
              <span className="text-xs font-bold tracking-[0.3em] text-white/30 uppercase mb-2 block">
                Neural Pipeline
              </span>
              <h3 className="text-lg font-display italic text-white tracking-tight">
                {title || loadingFacts[loreIndex]}
              </h3>
            </motion.div>
          </AnimatePresence>

          <div className="h-0.5 w-full bg-white/5 rounded-full overflow-hidden relative">
            <motion.div 
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-amber-500/20 via-amber-200 to-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.5)]"
              initial={{ width: "0%" }}
              animate={{ width: "95%" }}
              transition={{ duration: 25, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
          
          <div className="mt-6 flex justify-between items-center px-1">
             <span className="text-[10px] font-bold tracking-widest text-white/20 uppercase">
               Syncing 24k Archive
             </span>
             <motion.span 
               className="text-[10px] font-mono text-amber-200/40"
               animate={{ opacity: [0.3, 0.7, 0.3] }}
               transition={{ duration: 2, repeat: Infinity }}
             >
               V.PRIME_ELITE
             </motion.span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
