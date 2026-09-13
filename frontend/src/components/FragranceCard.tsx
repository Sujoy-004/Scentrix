'use client';

import React, { useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Star, Sparkles } from 'lucide-react';
import { useAppStore } from '@/stores/app-store';
import { getFamilyAsset } from '@/lib/family-mapping';
import { computeReason } from '@/lib/reason-engine';
import { useToastStore } from '@/stores/toast-store';
import { RatingControls } from './RatingControls';

interface FragranceCardProps {
  frag: any;
  index?: number;
  showMatch?: boolean;
}

const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();

export function FragranceCard({ frag, index = 0, showMatch = true }: FragranceCardProps) {
  const router = useRouter();
  const cardRef = useRef<HTMLElement>(null);
  const { quizResponses } = useAppStore();

  const isRated = quizResponses.some(r => r.fragrance_id === frag.id);

  const addToast = useToastStore((s) => s.addToast);

  const handleOpen = () => {
    if (!frag.id) return;
    router.push(`/fragrances/${encodeURIComponent(frag.id)}`);
  };

  const handleRemoveRating = (e: React.MouseEvent) => {
    e.stopPropagation();
    useAppStore.setState((state) => ({
      quizResponses: state.quizResponses.filter(r => r.fragrance_id !== frag.id)
    }));
    addToast({ message: `Removed rating for ${frag.name}`, type: 'info' });
  };

  const familyLookup = frag.family || frag.top_accords?.[0] || frag.brand || 'all';
  const familyAsset = getFamilyAsset(familyLookup);
  const displayFamily = frag.family || (frag.top_accords?.[0] || 'Universal');

  return (
    <motion.article
      ref={cardRef}
      className="fragrance-card-elite frag-list-card flex flex-col"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      onClick={handleOpen}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleOpen(); } }}
      role="button"
      tabIndex={0}
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '24px',
        overflow: 'hidden',
        backdropFilter: 'blur(20px)',
        position: 'relative',
        height: '100%',
        cursor: 'pointer',
        transition: 'all 0.4s cubic-bezier(0.23, 1, 0.32, 1)'
      }}
      whileHover={{ 
        y: -8, 
        borderColor: 'rgba(255, 255, 255, 0.2)',
        backgroundColor: 'rgba(255, 255, 255, 0.04)'
      }}
      whileFocus={{ borderColor: 'rgba(255, 255, 255, 0.25)' }}
    >
      {/* Upper Visual Area */}
      <div className="relative aspect-[4/5] overflow-hidden">
        <img
          src={frag.image_url || familyAsset?.src || '/assets/family/all.webp'}
          alt={frag.name}
          className="w-full h-full object-cover transition-transform duration-700 hover:scale-110"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0a] via-transparent to-transparent opacity-80" />
        
        {/* Floating Badges */}
        <div className="absolute top-4 left-4 flex flex-col gap-2">
           {showMatch && frag.match_score && (
             <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/20 border border-amber-500/30 backdrop-blur-md">
               <Sparkles size={12} className="text-amber-400" />
                <span className="text-[10px] font-bold text-amber-200 uppercase tracking-tighter">{frag.match_score}% Match To Your Taste</span>
             </div>
           )}

           <div className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
              <span className="text-[10px] font-medium text-white/50 uppercase tracking-tighter">{titleCase(displayFamily)}</span>
           </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-6 flex flex-col flex-1">
        <p className="text-[10px] uppercase tracking-[0.2em] text-white/30 font-bold mb-1">{frag.brand}</p>
        <h3 className="text-lg font-light text-white mb-4 line-clamp-1">{frag.name}</h3>
        
        <div className="flex flex-wrap gap-2 mb-6">
          {(frag.top_notes?.length ? frag.top_notes : frag.top_accords)?.slice(0, 2).map((note: string) => (
            <span key={note} className="text-[9px] uppercase tracking-widest px-2 py-1 bg-white/5 border border-white/10 rounded-md text-white/60">
              {titleCase(note)}
            </span>
          ))}
        </div>

        {(() => {
          const reasonText = computeReason(frag, quizResponses);
          return reasonText ? (
            <motion.div
              className="mb-5 p-4 rounded-xl bg-white/[0.06] border border-amber-500/20"
              whileHover={{
                backgroundColor: 'rgba(255, 255, 255, 0.12)',
                borderColor: 'rgba(251, 191, 36, 0.5)',
                scale: 1.02
              }}
              transition={{ duration: 0.2 }}
            >
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-amber-300 mb-1.5">Why Recommended</p>
              <p className="text-sm leading-relaxed text-white/90">{reasonText}</p>
            </motion.div>
          ) : null;
        })()}

        <div className="mt-auto flex items-center justify-between">
           <div className="flex items-center gap-1">
             <span className="text-amber-500 text-sm">★</span>
             <span className="text-xs font-bold text-white/80">{frag.rating ? frag.rating.toFixed(1) : 'N/A'}</span>
           </div>
           
           {isRated ? (
             <button
               onClick={handleRemoveRating}
               className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider text-amber-300 bg-amber-500/10 border border-amber-500/30 transition-colors hover:bg-amber-500/20"
             >
               <Star size={14} fill="currentColor" /> Rated
             </button>
           ) : (
             <span className="text-[10px] uppercase tracking-widest text-white/30">
               View details →
             </span>
           )}
        </div>

        {!isRated && (
          <div className="mt-3">
            <RatingControls
              target={{
                fragrance_id: frag.id,
                name: frag.name,
                brand: frag.brand,
                top_notes: frag.top_notes,
                accords: frag.top_accords,
              }}
            />
          </div>
        )}
      </div>
    </motion.article>
  );
}