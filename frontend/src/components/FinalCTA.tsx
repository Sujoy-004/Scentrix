'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { CheckCircle2, ArrowRight } from 'lucide-react';
import '@/styles/final-cta.css';

export function FinalCTA() {
  const router = useRouter();

  const trustBadges = [
    "Elite Provenance",
    "Neural Graph Security",
    "Verified Critics",
    "Concierge Support"
  ];

  return (
    <section className="final-cta">
      <div className="glow-effect" />
      
      <div className="container mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="final-cta-container"
        >
          <h2 className="final-cta-title">Manifest Your Presence.</h2>
          <p className="final-cta-subtitle">Join the collective of collectors who navigate the ScentScape through architectural intelligence.</p>

          <motion.button 
            whileHover={{ scale: 1.05, y: -4 }}
            whileTap={{ scale: 0.95 }}
            className="final-cta-button"
            onClick={() => router.push('/onboarding/quiz')}
          >
            Start Your Protocol <ArrowRight className="ml-2" size={18} />
          </motion.button>

          <div className="badges-row-elite">
            {trustBadges.map((badge, idx) => (
              <motion.div 
                key={badge}
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                transition={{ delay: 0.1 * idx }}
                className="badge-item-elite"
              >
                <CheckCircle2 size={12} className="icon-check" />
                {badge}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
