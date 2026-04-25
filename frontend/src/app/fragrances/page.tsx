'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, useScroll, useSpring } from 'framer-motion';
import { api, type FragranceCatalogItem } from '@/lib/api';
import { getFamilyAsset } from '@/lib/family-mapping';
import { VideoScrubber } from '@/components/VideoScrubber';
import { ScentrixLogo } from '@/components/ScentrixLogo';
import { DiscoveryNeuralLoader } from '@/components/DiscoveryNeuralLoader';
import { FragranceCard } from '@/components/FragranceCard';
import { AnimatePresence } from 'framer-motion';
import { Suspense } from 'react';
import './fragrances.css';

const FAMILIES = [
  'Amber', 'Animalic', 'Aquatic', 'Aromatic', 'Citrus', 'Earthy',
  'Floral', 'Fresh', 'Fruity', 'Gourmand', 'Green', 'Leather',
  'Musky', 'Oriental', 'Powdery', 'Smoky', 'Spicy', 'Woody'
];
const VIDEO_FAMILIES = ['animalic', 'aquatic', 'citrus', 'earthy', 'floral', 'fresh', 'fruity', 'leather', 'aromatic', 'amber', 'all'];

const BOTTLE_COLORS: Record<string, string> = {
  '1': 'linear-gradient(135deg, #6b3a1f, #c87941)',
  '2': 'linear-gradient(135deg, #b8860b, #ffe08a)',
  '3': 'linear-gradient(135deg, #1a4a1a, #4caf50)',
  '4': 'linear-gradient(135deg, #4a3728, #8b6347)',
  '5': 'linear-gradient(135deg, #8b1a4a, #e91e8c)',
  '6': 'linear-gradient(135deg, #1a3a5c, #4a90d9)',
  '7': 'linear-gradient(135deg, #8b4513, #ff8c00)',
  '8': 'linear-gradient(135deg, #1a2a3a, #4a6fa5)',
  'all': 'linear-gradient(135deg, #c9a86c, #f0d090)',
};
const PER_PAGE = 20;

export default function FragrancesPage() {
  return (
    <Suspense fallback={<DiscoveryNeuralLoader title="Loading Archive..." />}>
      <FragrancesContent />
    </Suspense>
  );
}

function FragrancesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const gridRef = useRef<HTMLDivElement>(null);

  const [items, setItems] = useState<FragranceCatalogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const [sortBy, setSortBy] = useState<'rating' | 'name' | 'match'>('rating');
  const [filterFamily, setFilterFamily] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const q = searchParams.get('q') || '';
    setSearchQuery(q);
  }, [searchParams]);

  const [page, setPage] = useState(1);
  const [jumpPage, setJumpPage] = useState('');

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const offset = (page - 1) * PER_PAGE;
        const result = (await api.getFragranceCatalog(PER_PAGE, offset, {
          q: searchQuery || undefined,
          family: filterFamily || undefined,
          sort: sortBy || undefined,
        })) as { items: FragranceCatalogItem[]; total: number };

        const rawItems = result.items || [];
        const uniqueItems = Array.from(
          new Map(rawItems.map((item: FragranceCatalogItem) => [item.id, item])).values()
        );

        setItems(uniqueItems);
        setTotal(result.total || 0);
      } catch (err) {
        console.error('Failed to load catalog:', err);
        setItems([]);
        setTotal(0);
      } finally {
        setIsLoading(false);
      }
    };

    const timer = setTimeout(load, searchQuery ? 300 : 0);
    return () => clearTimeout(timer);
  }, [page, filterFamily, searchQuery, sortBy]);

  useEffect(() => {
    setPage(1);
  }, [filterFamily, searchQuery, sortBy]);

  useEffect(() => {
    if (!gridRef.current || isLoading) return;
    gridRef.current.querySelectorAll('.frag-list-card').forEach((card: Element, i: number) => {
      (card as HTMLElement).style.animationDelay = `${i * 40}ms`;
      card.classList.add('card-enter');
    });
  }, [items, isLoading]);

  if (isLoading && items.length === 0) {
    return (
      <div className="browse-page">
        <DiscoveryNeuralLoader />
      </div>
    );
  }

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div className="browse-page">
      <VideoScrubber
        videoPath="/assets/top_hero.mp4"
        isFixed={true}
      />
      <FamilyBackground family={filterFamily || 'all'} />


      {/* ── Floating Atmospheric Filter Nexus ── */}
      <div className="browse-layout">
        <div className="browse-sidebar" aria-label="Aetheric Filters">
          <div className="sidebar-section">
            <h2 className="sidebar-label">Olfactive DNA Strands</h2>
            <div className="family-button-grid">
              <FamilyWideBtn
                name="All Fragments"
                slug="all"
                active={filterFamily === ''}
                onClick={() => setFilterFamily('')}
              />
              {FAMILIES.map((f) => (
                <FamilyWideBtn
                  key={f}
                  name={f}
                  slug={f.toLowerCase()}
                  active={filterFamily === f.toLowerCase()}
                  onClick={() => setFilterFamily(f.toLowerCase())}
                />
              ))}
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sort-btn-group" style={{ flexDirection: 'row', overflowX: 'auto', gap: '8px' }}>
              {(['rating', 'match', 'name'] as const).map((s) => (
                <button
                  key={s}
                  className={`sort-btn ${sortBy === s ? 'active' : ''}`}
                  onClick={() => setSortBy(s)}
                  style={{ borderRadius: '40px', padding: '10px 24px', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  {s === 'rating' ? '★ Pure Rating' : s === 'match' ? '⚡ Genetic Match' : 'A–Z Sequence'}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Cinematic Main Content ── */}
        <main className="browse-main">
          <header className="discovery-header">
            <h1 className="display-lg text-gradient-amber">The Olfactive Archive</h1>
          </header>



          {isLoading ? (
            <div style={{ padding: '60px 0', minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <DiscoveryNeuralLoader title="Sequencing olfactory graph..." />
            </div>
          ) : items.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-24 gap-6 text-center max-w-md mx-auto"
            >
              <div className="w-16 h-[1px] bg-primary/30 mb-2"></div>
              <h2 className="display-sm text-white italic">Olfactive Void</h2>
              <p className="text-white/50 text-sm leading-relaxed">
                Specific combinations like <span className="text-primary italic">"{searchQuery}"</span> are rare masterpieces. 
                Our 24k collection is vast, but this exact resonance hasn't been captured yet.
              </p>
              <div className="flex gap-4 mt-4">
                <button 
                  onClick={() => { setFilterFamily(''); setSearchQuery(''); }} 
                  className="btn btn-primary px-8"
                >
                  Clear Resonance
                </button>
              </div>
            </motion.div>
          ) : (
            <div className="fragrances-grid" ref={gridRef}>
              {items.map((frag, idx) => (
                <FragranceCard
                  key={frag.id}
                  frag={{
                    ...frag,
                    rating: frag.rating || 3.8,
                    match_score: frag.match_score || 82
                  }}
                  index={idx}
                />
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="discovery-pagination">
              <motion.button
                whileHover={{ x: -4 }}
                whileTap={{ scale: 0.95 }}
                className="page-nav-btn prev"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <span className="nav-arrow">←</span>
              </motion.button>

              <div className="page-numbers-nexus">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let p = i + 1;
                  if (page > 3) p = page - 3 + (i + 1);
                  if (p > totalPages) return null;

                  const isActive = p === page;

                  return (
                    <motion.button
                      key={p}
                      className={`page-num-btn ${isActive ? 'active' : ''}`}
                      onClick={() => setPage(p)}
                      whileHover={{ y: -2, scale: 1.1 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      {isActive && (
                        <motion.div
                          layoutId="active-pill"
                          className="active-pill-glow"
                          transition={{ type: "spring", stiffness: 350, damping: 30 }}
                        />
                      )}
                      <span className="num-label">{p}</span>
                    </motion.button>
                  );
                })}
              </div>

              <motion.button
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.95 }}
                className="page-nav-btn next"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <span className="nav-arrow">→</span>
              </motion.button>

              <div className="jump-nexus">
                <input
                  className="jump-input"
                  placeholder="GOTO"
                  value={jumpPage}
                  onChange={(e) => setJumpPage(e.target.value.replace(/\D/g, ''))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const p = parseInt(jumpPage);
                      if (p >= 1 && p <= totalPages) {
                        setPage(p);
                        setJumpPage('');
                      }
                    }
                  }}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function FamilyBackground({ family }: { family: string }) {
  const asset = getFamilyAsset(family || 'all');

  if (asset.error) {
    return (
      <div className="family-discovery-bg flex items-center justify-center bg-black/80">
        <span className="text-[10px] tracking-widest text-[#f4bb92]/40 italic uppercase">{asset.error}</span>
      </div>
    );
  }

  return (
    <div className="family-discovery-bg">
      <img
        src={asset.src!}
        alt={family}
        className="family-discovery-img"
      />
      <div className="family-discovery-dimmer" />

      {/* ── Holographic Parallax: Triple-Vapor Scentscape ── */}
      <div className="spatial-vapor-nexus">
        <div className="vapor-cloud vapor-layer-1" />
        <div className="vapor-cloud vapor-layer-2" />
        {/* Layer 3 culled for composite performance */}
      </div>
    </div>
  );
}


function FamilyWideBtn({ name, slug, active, onClick }: { name: string; slug: string; active: boolean; onClick: () => void }) {
  const asset = getFamilyAsset(slug);

  return (
    <button
      className={`family-btn-wide ${active ? 'active' : ''}`}
      onClick={onClick}
    >
      <div className="btn-structure-pillar">
        <div className="btn-image-container">
          {asset.error ? (
            <div className="btn-error-placeholder">
              <span className="error-text">{asset.error}</span>
            </div>
          ) : (
            <img
              src={asset.src!}
              alt={name}
              className="btn-bg-img"
              loading="lazy"
            />
          )}
          <div className="btn-overlay-glass" />
        </div>
        <div className="btn-shimmer-effect" />
        <span className="btn-label-elite">{name}</span>
      </div>
    </button>
  );
}

function BottleVisual({ id, color }: { id: string; color?: string }) {
  const finalColor = color || BOTTLE_COLORS[id] || BOTTLE_COLORS[parseInt(id) % 8 || 1] || 'linear-gradient(135deg, #f4bb92, #e4c285)';
  return (
    <div className="dna-core-molecule">
      <div className="dna-orbit dna-orbit-1" style={{ borderColor: color }} />
      <div className="dna-orbit dna-orbit-2" style={{ borderColor: color }} />
      <div className="dna-core-sphere" style={{ background: finalColor }}>
        <div className="dna-glint" />
      </div>
      <div className="dna-label-tag">FRAGRANCE DNA</div>
    </div>
  );
}

