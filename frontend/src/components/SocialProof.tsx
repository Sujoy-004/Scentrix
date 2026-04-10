'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Users, Zap, Library, Quote, Star } from 'lucide-react';
import '@/styles/social-proof.css';

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
  hidden: { opacity: 0, scale: 0.9, y: 20 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { type: 'spring' as const, stiffness: 50, damping: 20 }
  }
};

export function SocialProof() {
  const stats = [
    { icon: <Users size={24} />, value: "5,130", label: "Elite Members" },
    { icon: <Zap size={24} />, value: "91.5%", label: "Satisfaction" },
    { icon: <Library size={24} />, value: "2K+", label: "Masterpieces" }
  ];

  const testimonials = [
    {
      name: 'Sarah M.',
      rating: 5,
      text: 'Finally found a fragrance that matches my personality perfectly. The AI recommendations are incredibly accurate!',
      match: '92% Match',
    },
    {
      name: 'James L.',
      rating: 5,
      text: "Best discovery platform for fragrances. I've found three new signatures in just a month.",
      match: '88% Match',
    },
    {
      name: 'Emma R.',
      rating: 5,
      text: 'Love the community ratings and detailed notes breakdowns. Makes choosing so much easier.',
      match: '95% Match',
    },
  ];

  return (
    <section className="social-proof">
      <div className="container mx-auto px-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false }}
          className="social-proof-header text-center mb-24"
        >
          <h2 className="text-3xl font-display italic text-white">Loved by the Collection</h2>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: false, margin: "-100px" }}
          className="stats-grid-elite"
        >
          {stats.map((stat, idx) => (
            <motion.div 
              key={idx}
              variants={itemVariants}
              className="stat-card-elite"
            >
              <div className="stat-icon text-primary/40 mb-2">{stat.icon}</div>
              <div className="stat-value">{stat.value}</div>
              <div className="stat-label">{stat.label}</div>
            </motion.div>
          ))}
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: false, margin: "-100px" }}
          className="testimonials-grid-elite"
        >
          {testimonials.map((t, idx) => (
            <motion.div 
              key={idx}
              variants={itemVariants}
              whileHover={{ y: -8 }}
              className="testimonial-card-elite group"
            >
              <Quote className="quote-icon" size={64} />
              
              <div className="stars-row">
                {[...Array(t.rating)].map((_, i) => (
                  <Star key={i} size={12} fill="var(--color-primary)" stroke="none" />
                ))}
              </div>

              <p className="testimonial-text">"{t.text}"</p>

              <div className="testimonial-footer">
                <span className="client-name">{t.name}</span>
                <span className="match-badge">
                  {t.match}
                </span>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
