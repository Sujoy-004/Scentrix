'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Star, ShieldCheck, Zap, Library } from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2,
    }
  }
};

const stepVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring' as const, stiffness: 60, damping: 20 }
  }
};

export function HowItWorks() {
  const steps = [
    {
      id: 1,
      icon: <Star size={32} />,
      title: "Rate Your Favorites",
      description: "Answer quick questions about your favorite fragrances. Rate them on sweetness, woodiness, and intensity.",
      visual: <div className="w-12 h-12 rounded-full border border-primary/20 flex items-center justify-center opacity-20"><Star size={24} /></div>
    },
    {
      id: 2,
      icon: <ShieldCheck size={32} />,
      title: "AI-Powered Matching",
      description: "Our GraphSAGE AI analyzes your taste profile and compares it with 5,130+ fragrances in our database.",
      visual: <div className="w-12 h-12 rounded-full border border-primary/20 flex items-center justify-center opacity-20"><Zap size={24} /></div>
    },
    {
      id: 3,
      icon: <Library size={32} />,
      title: "Explore & Discover",
      description: "Browse personalized matches, view detailed notes, and save favorites to your private collection.",
      visual: <div className="w-12 h-12 rounded-full border border-primary/20 flex items-center justify-center opacity-20"><Library size={24} /></div>
    }
  ];

  return (
    <section className="how-it-works py-32 relative overflow-hidden">
      <div className="container mx-auto px-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-24"
        >
          <h2 className="section-title text-center" style={{ marginBottom: '0.5rem', width: '100%', display: 'block' }}>The Alchemist's Path</h2>
          <p className="section-subtitle text-center" style={{ marginTop: '0', marginBottom: '4rem', width: '100%', display: 'block' }}>
            Three steps to your architectural scent profile
          </p>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="steps-grid grid grid-cols-1 md:grid-cols-3 gap-12"
        >
          {steps.map((step) => (
            <motion.div 
              key={step.id}
              variants={stepVariants}
              className="step-card group relative p-10 rounded-3xl border border-white/5 bg-white/2 hover:bg-white/5 transition-colors text-center"
            >
              <div className="step-number absolute -top-5 left-1/2 -translate-x-1/2 w-10 h-10 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold shadow-lg shadow-primary/20">
                {step.id}
              </div>
              
              <motion.div 
                whileHover={{ scale: 1.1, rotate: 5 }}
                className="step-emoji mb-8 flex justify-center text-primary"
              >
                {step.icon}
              </motion.div>

              <h3 className="step-heading text-xl font-display italic mb-4">{step.title}</h3>
              <p className="step-description text-muted text-sm leading-relaxed mb-8">
                {step.description}
              </p>

              <div className="flex justify-center mt-auto">
                {step.visual}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
