'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ScentrixLogo } from './ScentrixLogo';

interface DiscoveryLoaderProps {
  title?: string;
}

export function DiscoveryNeuralLoader({ title }: DiscoveryLoaderProps) {
  const [loreIndex, setLoreIndex] = useState(0);
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
    const timer = setInterval(() => {
      setLoreIndex((prev) => (prev + 1) % loadingFacts.length);
    }, 2800);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="discovery-loader" style={{
      '--quiz-accent': '#f4bb92',
      '--quiz-glow': 'rgba(244,187,146,0.2)',
      '--quiz-ink': '#f4bb92',
    } as any}>
      <div className="loader-particle-stream">
        {[...Array(8)].map((_, i) => (
          <motion.div 
            key={i}
            className="loader-dna-strand"
            initial={{ y: -100, x: Math.random() * 100 - 50, opacity: 0 }}
            animate={{ 
              y: 800, 
              opacity: [0, 0.4, 0],
              height: [20, 120, 20] 
            }}
            transition={{ 
              duration: 3 + Math.random() * 5, 
              repeat: Infinity, 
              delay: i * 0.5 
            }}
          />
        ))}
      </div>

      <motion.div 
        className="loader-minimal-content"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          gap: '2.5rem'
        }}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1.5, ease: "easeOut" }}
      >
        <div className="loader-molecule-center">
          <ScentrixLogo size={140} />
          <motion.div 
            className="molecular-orbital-glow"
            animate={{ 
              rotate: 360,
              scale: [1, 1.1, 1],
              opacity: [0.1, 0.3, 0.1]
            }}
            transition={{ 
              rotate: { duration: 20, repeat: Infinity, ease: "linear" },
              scale: { duration: 4, repeat: Infinity, ease: "easeInOut" },
              opacity: { duration: 4, repeat: Infinity, ease: "easeInOut" }
            }}
          />
        </div>
        
        <div className="loader-minimal-status">
          <AnimatePresence mode="wait">
            <motion.span 
              key={loreIndex}
              className="status-label text-gradient-amber"
              initial={{ opacity: 0, y: 15, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -15, filter: 'blur(8px)' }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              {title || loadingFacts[loreIndex]}
            </motion.span>
          </AnimatePresence>

          <div className="status-progress-bar">
            <motion.div 
              className="status-progress-fill" 
              initial={{ width: "0%" }}
              animate={{ width: "98%" }}
              transition={{ duration: 30, ease: "easeInOut" }}
            />
          </div>
          <span className="loader-percentage-hint">
            SYNCHRONIZING OLFACIVE ARCHIVE
          </span>
        </div>
      </motion.div>
    </div>
  );
}
