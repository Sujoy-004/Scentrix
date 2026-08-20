'use client';

import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { FAMILIES } from '@/lib/families';
import { getFamilyAsset } from '@/lib/family-mapping';
import '@/styles/fragrance-families.css';
import './families.css';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 30 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: 'spring' as const, stiffness: 60, damping: 20 },
  },
};

export default function FamiliesPage() {
  const router = useRouter();

  return (
    <div className="families-page">
      <div className="families-container">
        <motion.header
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="families-header"
        >
          <p className="families-eyebrow">The Scentrix Collection</p>
          <h1 className="families-title">Fragrance Families</h1>
          <p className="families-subtitle">
            Eighteen olfactive worlds, each with its own identity and story. Discover the family that speaks to your skin.
          </p>
        </motion.header>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="families-grid"
        >
          {FAMILIES.map((family) => {
            const asset = getFamilyAsset(family.slug);
            return (
              <motion.div
                key={family.slug}
                variants={cardVariants}
                className="elite-family-card"
                role="button"
                tabIndex={0}
                aria-label={`Explore the ${family.name} fragrance family`}
                onClick={() => router.push(`/families/${family.slug}`)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    router.push(`/families/${family.slug}`);
                  }
                }}
              >
                <div className="family-image-container">
                  {asset.error ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                      <span className="text-[10px] text-[#f4bb92]/50 italic">{asset.error}</span>
                    </div>
                  ) : (
                    <img
                      src={asset.src!}
                      alt={family.name}
                      className="family-image"
                      loading="lazy"
                    />
                  )}
                  <div className="family-overlay" />
                </div>

                <div className="family-content">
                  <h2 className="family-name">{family.name}</h2>
                  <p className="family-desc">{family.tagline}</p>
                  <div className="explore-trigger">
                    <span className="explore-text">Explore Collection</span>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </div>
  );
}
