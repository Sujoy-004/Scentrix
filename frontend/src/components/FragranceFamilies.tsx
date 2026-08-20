'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { getFamilyAsset } from '@/lib/family-mapping';
import '@/styles/fragrance-families.css';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
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

// Expanded list of 18 families (excluding 'all.png' for the primary grid)
const families = [
  { name: 'Floral', slug: 'floral', description: 'Delicate Petals' },
  { name: 'Woody', slug: 'woody', description: 'Ancient Forests' },
  { name: 'Citrus', slug: 'citrus', description: 'Zesty Vibrance' },
  { name: 'Oriental', slug: 'oriental', description: 'Exotic Splendor' },
  { name: 'Amber', slug: 'amber', description: 'Resinous Warmth' },
  { name: 'Smoky', slug: 'smoky', description: 'Incense & Embers' },
  { name: 'Fruity', slug: 'fruity', description: 'Sun-Drenched' },
  { name: 'Gourmand', slug: 'gourmand', description: 'Divine Sweets' },
  { name: 'Leather', slug: 'leather', description: 'Tanned Elegance' },
  { name: 'Spicy', slug: 'spicy', description: 'Warm Sands' },
  { name: 'Aquatic', slug: 'aquatic', description: 'Oceanic Mist' },
  { name: 'Aromatic', slug: 'aromatic', description: 'Herbal Harmony' },
  { name: 'Green', slug: 'green', description: 'Verdant Leaves' },
  { name: 'Musky', slug: 'musky', description: 'Velvet Aura' },
  { name: 'Powdery', slug: 'powdery', description: 'Silk Dust' },
  { name: 'Earthy', slug: 'earthy', description: 'Foraged Roots' },
  { name: 'Animalic', slug: 'animalic', description: 'Raw Sensuality' },
  { name: 'Fresh', slug: 'fresh', description: 'Crisp Morning' },
];

export function FragranceFamilies() {
  const router = useRouter();

  return (
    <section className="fragrance-families">
      <div className="families-container">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false }}
          className="text-center mb-24"
        >
          <h2 className="section-title italic mb-6">Discovery Families</h2>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: false, margin: "-100px" }}
          className="families-grid"
        >
          {families.slice(0, 10).map((family) => (
            <motion.div 
              key={family.slug}
              variants={cardVariants}
              className="elite-family-card"
              onClick={() => router.push('/families')}
            >
              <div className="family-image-container">
                {(() => {
                  const asset = getFamilyAsset(family.slug);
                  if (asset.error) {
                    return (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                        <span className="text-[10px] text-[#f4bb92]/50 italic">{asset.error}</span>
                      </div>
                    );
                  }
                  return (
                    <img 
                      src={asset.src!} 
                      alt={family.name} 
                      className="family-image"
                      loading="lazy"
                    />
                  );
                })()}
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
                  <span className="explore-text">Explore Collection</span>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: false }}
          className="flex justify-center mt-32"
        >
          <motion.button
            whileHover={{ scale: 1.05, y: -4 }}
            whileTap={{ scale: 0.95 }}
            className="btn btn-outline border-primary/30 text-primary px-12 py-5 text-xs tracking-[0.3em] font-bold"
            onClick={() => router.push('/families')}
          >
            Explore More
          </motion.button>
        </motion.div>
      </div>
    </section>
  );
}
