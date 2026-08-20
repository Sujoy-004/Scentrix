'use client';

import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Star, Sparkles } from 'lucide-react';
import { useAppStore } from '@/stores/app-store';
import { useSubmitRating } from '@/lib/hooks';
import { getFamilyAsset } from '@/lib/family-mapping';
import { computeReason } from '@/lib/reason-engine';
import { useToastStore } from '@/stores/toast-store';

interface FragranceCardProps {
  frag: any;
  index?: number;
  showMatch?: boolean;
}

export function FragranceCard({ frag, index = 0, showMatch = true }: FragranceCardProps) {
  const cardRef = useRef<HTMLElement>(null);
  
  const { quizResponses, addQuizResponse } = useAppStore();
  const submitRating = useSubmitRating();

  // Check if already rated either in local store (for guests) or server collection (for users)
  const isRated = quizResponses.some(r => r.fragrance_id === frag.id);

  const addToast = useToastStore((s) => s.addToast);

  const handleRate = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isRated) {
      useAppStore.setState((state) => ({
        quizResponses: state.quizResponses.filter(r => r.fragrance_id !== frag.id)
      }));
      addToast({ message: `Removed rating for ${frag.name}`, type: 'info' });
    } else {
      addQuizResponse({
        fragrance_id: frag.id,
        rating: 8,
        name: frag.name,
        brand: frag.brand,
        top_notes: frag.top_notes,
        accords: frag.top_accords,
      });
      submitRating.mutate({ fragranceId: frag.id, rating: 8 });
      addToast({
        message: `Rated ${frag.name} — refining your matches`,
        type: 'success',
        action: {
          label: 'Undo',
          onClick: () => {
            useAppStore.setState((state) => ({
              quizResponses: state.quizResponses.filter(r => r.fragrance_id !== frag.id)
            }));
          },
        },
      });
    }
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
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '24px',
        overflow: 'hidden',
        backdropFilter: 'blur(20px)',
        position: 'relative',
        height: '100%',
        transition: 'all 0.4s cubic-bezier(0.23, 1, 0.32, 1)'
      }}
      whileHover={{ 
        y: -10, 
        borderColor: 'rgba(255, 255, 255, 0.2)',
        backgroundColor: 'rgba(255, 255, 255, 0.04)'
      }}
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
              <span className="text-[10px] font-medium text-white/50 uppercase tracking-tighter">{displayFamily}</span>
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
              {note}
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
           
           <div className="flex gap-2">
               <button
                onClick={handleRate}
                className={`p-2 transition-colors ${
                  isRated ? 'text-amber-400' : 'text-white/40 hover:text-white'
                }`}
              >
                <Star size={16} fill={isRated ? 'currentColor' : 'none'} />
              </button>
           </div>
        </div>
      </div>
    </motion.article>
  );
}
