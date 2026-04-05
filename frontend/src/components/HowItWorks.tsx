'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Star, ShieldCheck, Zap, Library } from 'lucide-react';
import '@/styles/how-it-works.css';

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
  hidden: { opacity: 0, scale: 0.95, y: 30 },
  visible: { 
    opacity: 1, 
    scale: 1,
    y: 0,
    transition: { type: 'spring' as const, stiffness: 50, damping: 20 }
  }
};

export function HowItWorks() {
  const steps = [
    {
      id: "01",
      icon: <Star size={40} />,
      title: "Archetypal Discovery",
      description: "Reveal your olfactory preferences through our high-fidelity rating interface, masking complexity with elegant interaction design.",
      visual: <div className="w-16 h-1 rounded-full bg-gradient-to-r from-primary/0 via-primary/40 to-primary/0" />
    },
    {
      id: "02",
      icon: <ShieldCheck size={40} />,
      title: "Neural Graph Mapping",
      description: "Our proprietary GraphSAGE engine scans 5,130 elite masterpieces, identifying latent patterns in your taste architecture.",
      visual: <div className="w-20 h-1 rounded-full bg-gradient-to-r from-primary/0 via-primary/50 to-primary/0" />
    },
    {
      id: "03",
      icon: <Library size={40} />,
      title: "Elite Curation",
      description: "Receive a distilled collection of architectural fragrances, synchronized across your profile for a seamless, cinematic encounter.",
      visual: <div className="w-24 h-1 rounded-full bg-gradient-to-r from-primary/0 via-primary/60 to-primary/0" />
    }
  ];

  return (
    <section className="how-it-works py-40">
      <div className="container mx-auto px-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-32"
        >
          <h2 className="section-title italic mb-4">Architectural Process</h2>
          <p className="section-subtitle mx-auto">Three pillars of the Scentrix elite discovery engine</p>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="steps-grid grid grid-cols-1 md:grid-cols-3 gap-10"
        >
          {steps.map((step) => (
            <motion.div 
              key={step.id}
              variants={stepVariants}
              className="step-card group"
            >
              <div className="step-number">
                {step.id}
              </div>
              
              <div className="step-emoji">
                {step.icon}
              </div>

              <h3 className="step-heading">{step.title}</h3>
              <p className="step-description">
                {step.description}
              </p>

              <div className="step-visual">
                {step.visual}
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
