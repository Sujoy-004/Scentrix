'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import '@/styles/fragrance-families.css';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    }
  }
};

const cardVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 30 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { type: 'spring' as const, stiffness: 60, damping: 20 }
  }
};

const families = [
  { name: 'Floral', slug: 'floral', description: 'Delicate Petals' },
  { name: 'Woody', slug: 'woody', description: 'Deep Roots' },
  { name: 'Citrus', slug: 'fresh', description: 'Bright Zest' },
  { name: 'Oriental', slug: 'oriental', description: 'Exotic Spices' },
  { name: 'Smoky', slug: 'smoky', description: 'Incense & Fire' },
  { name: 'Fruity', slug: 'fruity', description: 'Sun-Drenched' },
  { name: 'Gourmand', slug: 'gourmand', description: 'Divine Sweets' },
  { name: 'Leather', slug: 'leather', description: 'Tanned Earth' },
  { name: 'Spicy', slug: 'spicy', description: 'Warm Sands' },
  { name: 'Powdery', slug: 'powdery', description: 'Velvet Dust' },
];

export function FragranceFamilies() {
  const router = useRouter();

  return (
    <section className="fragrance-families">
      <div className="families-container">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <h2 className="section-title italic mb-4">Architectural Families</h2>
          <p className="section-subtitle mx-auto">Explore the scent foundations of the elite curators</p>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="families-grid"
        >
          {families.map((family) => (
            <motion.div 
              key={family.slug}
              variants={cardVariants}
              className="elite-family-card"
              onClick={() => router.push(`/fragrances?family=${family.slug}`)}
            >
              <div className="family-image-container">
                <img 
                  src={`/assets/families/${family.slug}.png`} 
                  alt={family.name} 
                  className="family-image"
                  loading="lazy"
                />
                <div className="family-overlay" />
              </div>
              
              <div className="family-content">
                <h3 className="family-name">
                  {family.name}
                </h3>
                <p className="family-desc">
                  {family.description}
                </p>
                <div className="explore-trigger">
                  <span className="explore-text">Explore</span>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
