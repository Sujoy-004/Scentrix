'use client';

import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bookmark, ShoppingBag, Info, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import { useAddToCollection, useRemoveFromWishlist, useWishlist } from '@/lib/hooks';
import { getFamilyAsset } from '@/lib/family-mapping';

interface FragranceCardProps {
  frag: any;
  index?: number;
  showMatch?: boolean;
}

export function FragranceCard({ frag, index = 0, showMatch = true }: FragranceCardProps) {
  const router = useRouter();
  const cardRef = useRef<HTMLElement>(null);
  
  const { isAuthenticated, wishlist, addToWishlist, removeFromWishlist } = useAppStore();
  const { data: serverCollection = [] } = useWishlist();
  
  const addMutation = useAddToCollection();
  const removeMutation = useRemoveFromWishlist();

  // Check if saved either in local store (for guests) or server collection (for users)
  const isSavedLocally = wishlist.includes(frag.id);
  const serverItem = serverCollection.find((item: any) => item.fragrance_neo4j_id === frag.id);
  const isSaved = isAuthenticated ? !!serverItem : isSavedLocally;

  const handleSaveToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (isAuthenticated) {
      if (isSaved && serverItem) {
        await removeMutation.mutateAsync(serverItem.id);
      } else {
        await addMutation.mutateAsync({ fragranceId: frag.id });
      }
    } else {
      // Guest flow
      if (isSaved) {
        removeFromWishlist(frag.id);
      } else {
        addToWishlist(frag.id);
      }
    }
  };

  const familyLookup = frag.family || frag.top_accords?.[0] || 'all';
  const familyAsset = getFamilyAsset(familyLookup);
  const displayFamily = frag.family || (frag.top_accords?.[0] || 'Universal');

  return (
    <motion.article
      ref={cardRef}
      className="fragrance-card-elite flex flex-col"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      onClick={() => router.push(`/fragrances/${frag.id}`)}
      style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '24px',
        overflow: 'hidden',
        backdropFilter: 'blur(20px)',
        cursor: 'pointer',
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
          src={frag.image_url || familyAsset.src || '/assets/family/all.png'}
          alt={frag.name}
          className="w-full h-full object-cover transition-transform duration-700 hover:scale-110"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0a] via-transparent to-transparent opacity-80" />
        
        {/* Floating Badges */}
        <div className="absolute top-4 left-4 flex flex-col gap-2">
           {showMatch && frag.match_score && (
             <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/20 border border-amber-500/30 backdrop-blur-md">
               <Sparkles size={12} className="text-amber-400" />
               <span className="text-[10px] font-bold text-amber-200 uppercase tracking-tighter">{frag.match_score}% Match</span>
             </div>
           )}
           <div className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
             <span className="text-[10px] font-medium text-white/50 uppercase tracking-tighter">{displayFamily}</span>
           </div>
        </div>

        {/* Action Buttons Overlay */}
        <div className="absolute top-4 right-4 flex flex-col gap-2 opacity-0 transition-opacity duration-300 group-hover:opacity-100" style={{ opacity: 1 /* for now keep visible */ }}>
          <button
            onClick={handleSaveToggle}
            className={`p-2.5 rounded-full backdrop-blur-xl transition-all duration-300 ${
              isSaved 
                ? 'bg-white text-black' 
                : 'bg-black/40 text-white border border-white/20 hover:bg-white/10'
            }`}
          >
            <Bookmark size={18} fill={isSaved ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="p-6 flex flex-col flex-1">
        <p className="text-[10px] uppercase tracking-[0.2em] text-white/30 font-bold mb-1">{frag.brand}</p>
        <h3 className="text-lg font-light text-white mb-4 line-clamp-1">{frag.name}</h3>
        
        <div className="flex flex-wrap gap-2 mb-6">
          {frag.top_notes?.slice(0, 2).map((note: string) => (
            <span key={note} className="text-[9px] uppercase tracking-widest px-2 py-1 bg-white/5 border border-white/10 rounded-md text-white/60">
              {note}
            </span>
          ))}
        </div>

        <div className="mt-auto flex items-center justify-between">
           <div className="flex items-center gap-1">
             <span className="text-amber-500 text-sm">★</span>
             <span className="text-xs font-bold text-white/80">{frag.rating ? frag.rating.toFixed(1) : '—'}</span>
           </div>
           
           <div className="flex gap-2">
             <button className="p-2 text-white/40 hover:text-white transition-colors">
               <Info size={16} />
             </button>
             <button className="p-2 text-white/40 hover:text-white transition-colors">
               <ShoppingBag size={16} />
             </button>
           </div>
        </div>
      </div>
    </motion.article>
  );
}
