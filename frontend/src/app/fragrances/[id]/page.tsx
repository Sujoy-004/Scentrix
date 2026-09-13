'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { api, type FragranceCatalogItem } from '@/lib/api';
import { getFamilyAsset } from '@/lib/family-mapping';
import { RatingControls } from '@/components/RatingControls';

const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();

export default function FragranceDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = typeof params?.id === 'string' ? decodeURIComponent(params.id) : '';

  const [frag, setFrag] = useState<FragranceCatalogItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setNotFound(true);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    setError(null);
    api
      .getFragranceDetail(id)
      .then((result) => {
        if (cancelled) return;
        setFrag(result?.data ?? null);
      })
      .catch((e: any) => {
        if (cancelled) return;
        const status = e?.response?.status;
        if (status === 404) {
          setNotFound(true);
        } else {
          setError('We could not load this fragrance. Please try again.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const handleBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push('/recommendations');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center"
        >
          <div className="mx-auto w-10 h-10 mb-6 border border-amber-500/30 rounded-full animate-spin" style={{ borderTopColor: '#f4bb92' }} />
          <p className="text-[10px] uppercase tracking-[0.3em] text-white/40">Loading fragrance...</p>
        </motion.div>
      </div>
    );
  }

  if (notFound || (!frag && !error)) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full text-center"
          style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '2rem', padding: '3rem 2rem' }}
        >
          <div className="w-14 h-14 mx-auto mb-6 rounded-full border border-white/10 flex items-center justify-center">
            <Sparkles size={22} className="text-amber-500/70" />
          </div>
          <h1 className="font-display italic text-2xl text-white mb-3">Fragrance not found</h1>
          <p className="text-sm text-white/50 mb-8 leading-relaxed">
            This scent has drifted out of our collection or the link is no longer valid.
          </p>
          <button
            onClick={() => router.push('/recommendations')}
            className="px-6 py-3 rounded-full text-[0.7rem] uppercase tracking-[0.15em] font-bold text-amber-200 border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 transition-colors"
          >
            View Recommendations
          </button>
        </motion.div>
      </div>
    );
  }

  if (error || !frag) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full text-center"
          style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '2rem', padding: '3rem 2rem' }}
        >
          <h1 className="font-display italic text-2xl text-white mb-3">Neural link lost</h1>
          <p className="text-sm text-white/50 mb-8 leading-relaxed">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 rounded-full text-[0.7rem] uppercase tracking-[0.15em] font-bold text-amber-200 border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 transition-colors"
          >
            Retry
          </button>
        </motion.div>
      </div>
    );
  }

  const familyLookup = frag.family || frag.accords?.[0] || frag.brand || 'all';
  const familyAsset = getFamilyAsset(familyLookup);

  return (
    <motion.div
      className="min-h-screen bg-black"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="mx-auto max-w-5xl px-6 py-8">
        <button
          onClick={handleBack}
          className="mb-8 inline-flex items-center gap-2 text-[0.65rem] uppercase tracking-[0.2em] text-white/40 hover:text-white/80 transition-colors"
        >
          <ArrowLeft size={14} /> Back
        </button>

        <div className="grid md:grid-cols-2 gap-10 items-start">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="relative aspect-[4/5] overflow-hidden rounded-3xl" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
              <img
                src={frag.image_url || familyAsset?.src || '/assets/family/all.webp'}
                alt={frag.name}
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0a] via-transparent to-transparent opacity-70" />
              {frag.family && (
                <div className="absolute top-4 left-4 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
                  <span className="text-[10px] font-medium text-white/50 uppercase tracking-tighter">{titleCase(frag.family)}</span>
                </div>
              )}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="flex flex-col"
          >
            <p className="text-[0.65rem] uppercase tracking-[0.25em] text-white/35 font-bold mb-2">{frag.brand}</p>
            <h1 className="font-display italic text-4xl text-white mb-6 leading-tight">{frag.name}</h1>

            <div className="flex flex-wrap gap-2 mb-8">
              {frag.year && (
                <span className="text-[10px] uppercase tracking-widest px-3 py-1.5 bg-white/5 border border-white/10 rounded-full text-white/60">{frag.year}</span>
              )}
              {frag.concentration && frag.concentration !== 'N/A' && (
                <span className="text-[10px] uppercase tracking-widest px-3 py-1.5 bg-white/5 border border-white/10 rounded-full text-white/60">{frag.concentration}</span>
              )}
              {frag.gender_label && frag.gender_label !== 'N/A' && (
                <span className="text-[10px] uppercase tracking-widest px-3 py-1.5 bg-white/5 border border-white/10 rounded-full text-white/60">{frag.gender_label}</span>
              )}
              {typeof frag.rating === 'number' && (
                <span className="text-[10px] uppercase tracking-widest px-3 py-1.5 bg-amber-500/10 border border-amber-500/25 rounded-full text-amber-200">★ {frag.rating.toFixed(1)} / 10</span>
              )}
            </div>

            {frag.description && (
              <p className="text-sm leading-relaxed text-white/65 mb-8">{frag.description}</p>
            )}

            {(frag.top_notes?.length || frag.middle_notes?.length || frag.base_notes?.length) && (
              <div className="mb-8 space-y-4">
                {[
                  { label: 'Top Notes', notes: frag.top_notes },
                  { label: 'Middle Notes', notes: frag.middle_notes },
                  { label: 'Base Notes', notes: frag.base_notes },
                ]
                  .filter((section) => section.notes?.length)
                  .map((section) => (
                    <div key={section.label}>
                      <p className="text-[0.6rem] uppercase tracking-[0.25em] text-amber-300/80 font-bold mb-2">{section.label}</p>
                      <div className="flex flex-wrap gap-2">
                        {section.notes!.map((note) => (
                          <span key={note} className="text-[10px] uppercase tracking-widest px-2.5 py-1 bg-white/5 border border-white/10 rounded-md text-white/60">
                            {titleCase(note)}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
              </div>
            )}

            <div className="mt-auto pt-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '1.25rem', padding: '1.25rem' }}>
              <RatingControls
                target={{
                  fragrance_id: frag.id,
                  name: frag.name,
                  brand: frag.brand,
                  top_notes: frag.top_notes,
                  accords: frag.accords,
                }}
              />
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}