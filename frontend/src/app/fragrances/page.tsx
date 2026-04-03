'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, useScroll, useSpring, useTransform } from 'framer-motion';
import { api, type FragranceCatalogItem } from '@/lib/api';
import './fragrances.css';

const FAMILIES = [
  'Amber', 'Animalic', 'Aquatic', 'Aromatic', 'Citrus', 'Earthy', 
  'Floral', 'Fresh', 'Fruity', 'Gourmand', 'Green', 'Leather', 
  'Musky', 'Oriental', 'Powdery', 'Smoky', 'Spicy', 'Woody'
];
const VIDEO_FAMILIES = ['animalic', 'aquatic', 'citrus', 'earthy', 'floral', 'fresh', 'fruity', 'leather', 'aromatic', 'amber', 'all'];
const EXTRACTED_FAMILIES = ['all', 'amber', 'aromatic', 'fruity', 'leather'];
const PER_PAGE = 21;

export default function FragrancesPage() {
  const router = useRouter();
  const gridRef = useRef<HTMLDivElement>(null);
  
  const [items, setItems] = useState<FragranceCatalogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  
  // States for filters/sorting
  const [sortBy, setSortBy] = useState<'rating' | 'name' | 'match'>('rating');
  const [filterFamily, setFilterFamily] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [jumpPage, setJumpPage] = useState('');

  // Load data from server
  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const offset = (page - 1) * PER_PAGE;
        const result = await api.getFragranceCatalog(PER_PAGE, offset, {
          q: searchQuery || undefined,
          family: filterFamily || undefined
        });
        
        setItems(result?.items || []);
        setTotal(result?.total || 0);
      } catch (err) {
        console.error('Failed to load catalog:', err);
        setItems([]);
        setTotal(0);
      } finally {
        setIsLoading(false);
      }
    };
    
    // Debounce search
    const timer = setTimeout(load, searchQuery ? 300 : 0);
    return () => clearTimeout(timer);
  }, [page, filterFamily, searchQuery]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [filterFamily, searchQuery]);

  // Load data from server

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
        <DiscoveryLoader />
      </div>
    );
  }

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div className="browse-page">
      <DiscoveryScrubber family={filterFamily || 'all'} />
      
      <div className="browse-header">
        <div className="browse-header-inner container">
          <div>
            <p className="browse-eyebrow">✦ Collection</p>
            <h1 className="browse-title">
              Explore <span className="text-gradient-amber">Fragrances</span>
            </h1>
          </div>
          <div className="browse-search-wrap">
            <span className="search-icon" aria-hidden="true">⌕</span>
            <input
              id="fragrance-search"
              className="browse-search"
              type="search"
              placeholder='Try "smoky vanilla" or "bergamot"…'
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search fragrances"
            />
          </div>
        </div>
      </div>

      <div className="browse-layout container">
        <aside className="browse-sidebar" aria-label="Filters">
          <div className="sidebar-section">
            <p className="sidebar-label">Olfactive Families</p>
            <div className="family-button-grid">
              <FamilyWideBtn 
                name="All Families" 
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
            <p className="sidebar-label">Sort Preferences</p>
            <div className="sort-btn-group">
              {(['rating', 'match', 'name'] as const).map((s) => (
                <button key={s} className={`sort-btn ${sortBy === s ? 'active' : ''}`} onClick={() => setSortBy(s)}>
                  {s === 'rating' ? '★ Highest Rated' : s === 'match' ? '⚡ Best Match' : 'A–Z Name'}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <main className="browse-main">
          <div className="browse-toolbar">
            <span className="result-count">
              Showing <strong>{items.length}</strong> of {total.toLocaleString()}
            </span>
            <div className="toolbar-sort-mobile">
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} className="sort-select-mobile" aria-label="Sort fragrances">
                <option value="rating">Highest Rated</option>
                <option value="match">Best Match</option>
                <option value="name">A–Z Name</option>
              </select>
            </div>
          </div>

          {items.length === 0 && !isLoading ? (
            <div className="empty-state">
              <p style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontStyle: 'italic', color: 'var(--color-on-surface-var)' }}>No fragrances found</p>
              <p style={{ color: 'var(--color-muted)', marginTop: '8px' }}>Refine your filters to discover more of the collection</p>
              <button className="btn btn-outline" style={{ marginTop: '24px' }} onClick={() => { setFilterFamily(''); setSearchQuery(''); }}>Clear All</button>
            </div>
          ) : (
            <div className={`fragrances-grid ${isLoading ? 'opacity-50' : ''}`} ref={gridRef}>
              {items.map((frag, idx) => (
                <FragCard 
                  key={frag.id} 
                  frag={{
                    ...frag,
                    rating: frag.rating || 3.8,
                    match_score: frag.match_score || 82
                  }} 
                  index={idx} 
                  onClick={() => router.push(`/fragrances/${frag.id}`)} 
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

function DiscoveryLoader() {
  return (
    <div className="discovery-loader-full">
      <motion.div 
        className="loader-4d-nexus"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="loader-supernova" />
        <motion.div 
          className="loader-logo-layer"
          animate={{ 
            y: [0, -10, 0],
            rotateY: [0, 15, 0],
            rotateX: [0, -10, 0]
          }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        >
          <img src="/assets/logo.png" alt="Scentrix Logo" className="loader-logo-img" />
        </motion.div>
        
        <motion.p 
          className="loader-synthesis-text"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          Neural Synthesis in Progress...
        </motion.p>
      </motion.div>
    </div>
  );
}

function DiscoveryScrubber({ family }: { family: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const currentImageRef = useRef<HTMLImageElement | null>(null);
  const frameRequestRef = useRef<number>(0);
  
  const { scrollYProgress } = useScroll();
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 45, damping: 22 });
  
  const isExtracted = EXTRACTED_FAMILIES.includes(family);
  const activeFamily = isExtracted ? family : 'all';

  const renderFrameToCanvas = (img: HTMLImageElement) => {
    const canvas = canvasRef.current;
    if (!canvas || !img.complete) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear and draw with cover aspect
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const canvasAspect = canvas.width / canvas.height;
    const imgAspect = img.width / img.height;
    let dW, dH, dX, dY;

    if (canvasAspect > imgAspect) {
      dW = canvas.width;
      dH = canvas.width / imgAspect;
      dX = 0;
      dY = (canvas.height - dH) / 2;
    } else {
      dH = canvas.height;
      dW = canvas.height * imgAspect;
      dX = (canvas.width - dW) / 2;
      dY = 0;
    }
    ctx.drawImage(img, dX, dY, dW, dH);
  };

  useEffect(() => {
    return smoothProgress.onChange(latest => {
      // Cancel previous frame to avoid over-rendering
      if (frameRequestRef.current) cancelAnimationFrame(frameRequestRef.current);
      
      frameRequestRef.current = requestAnimationFrame(() => {
        const idx = Math.min(Math.max(Math.floor(latest * 239) + 1, 1), 240);
        const frameStr = idx.toString().padStart(3, '0');
        const img = new Image();
        img.src = `/assets/${activeFamily}_extracted/ezgif-frame-${frameStr}.png`;
        img.onload = () => renderFrameToCanvas(img);
        currentImageRef.current = img;
      });
    });
  }, [activeFamily, smoothProgress]);

  // Handle Resize and Orientation
  useEffect(() => {
    const handleResize = () => {
      if (canvasRef.current) {
        canvasRef.current.width = window.innerWidth;
        canvasRef.current.height = window.innerHeight;
        if (currentImageRef.current) renderFrameToCanvas(currentImageRef.current);
      }
    };
    window.addEventListener('resize', handleResize, { passive: true });
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="discovery-scrubber-wrap">
      <div className="scrubber-overlay" />
      <canvas
        ref={canvasRef}
        className="scrubber-frame-canvas"
      />
    </div>
  );
}

function FamilyWideBtn({ name, slug, active, onClick }: { name: string; slug: string; active: boolean; onClick: () => void }) {
  const hasVideo = VIDEO_FAMILIES.includes(slug);

  return (
    <button
      className={`family-btn-wide ${active ? 'active' : ''}`}
      onClick={onClick}
    >
      {hasVideo ? (
        <video 
          autoPlay 
          loop 
          muted 
          playsInline 
          className="btn-bg-img"
          poster={`/assets/families/${slug}.png`}
        >
          <source src={`/assets/families/${slug}.mp4`} type="video/mp4" />
        </video>
      ) : (
        <img 
          src={`/assets/families/${slug}.png`} 
          alt={name} 
          className="btn-bg-img" 
          loading="lazy"
        />
      )}
      <div className="btn-overlay" />
      <span className="btn-label">{name}</span>
    </button>
  );
}

function FragCard({ frag, index, onClick }: { frag: any; index: number; onClick: () => void }) {
  const cardRef = useRef<HTMLElement>(null);
  const frameRef = useRef<number | null>(null);
  const cursorFxEnabledRef = useRef(false);
  const topNotes = frag.top_notes?.slice(0, 3) || [];
  const midNotes = frag.middle_notes?.slice(0, 2) || [];
  const baseNotes = frag.base_notes?.slice(0, 2) || [];
  const accords = frag.accords?.slice(0, 2) || [];

  const updateCursorVars = (x: number, y: number) => {
    const card = cardRef.current;
    if (!card) return;
    card.style.setProperty('--cursor-x', `${x}px`);
    card.style.setProperty('--cursor-y', `${y}px`);
  };

  useEffect(() => {
    cursorFxEnabledRef.current =
      typeof window !== 'undefined' &&
      window.matchMedia('(pointer: fine)').matches &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    return () => { if (frameRef.current !== null) cancelAnimationFrame(frameRef.current); };
  }, []);

  const handlePointerMove = (event: React.PointerEvent<HTMLElement>) => {
    if (!cursorFxEnabledRef.current) return;
    const card = cardRef.current;
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(() => { updateCursorVars(x, y); frameRef.current = null; });
  };

  const handlePointerEnter = () => { if (cursorFxEnabledRef.current) cardRef.current?.setAttribute('data-cursor-active', '1'); };
  const handlePointerLeave = () => {
    if (!cursorFxEnabledRef.current) return;
    const card = cardRef.current;
    if (!card) return;
    card.setAttribute('data-cursor-active', '0');
    updateCursorVars(card.clientWidth * 0.5, card.clientHeight * 0.5);
  };

  return (
    <article
      ref={cardRef}
      className="frag-list-card fragrance-card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      onPointerMove={handlePointerMove}
      onPointerEnter={handlePointerEnter}
      onPointerLeave={handlePointerLeave}
      aria-label={`${frag.name} by ${frag.brand}`}
      data-cursor-active="0"
    >
      <div className="frag-list-image">
        <div className="bottle-placeholder" aria-hidden="true">
          <div className="bottle-svg">
            <div className="bottle-glow" />
            <span style={{ fontSize: '3.5rem', position: 'relative', zIndex: 1 }}>🧴</span>
          </div>
        </div>
        <div className="match-badge" aria-label={`${frag.match_score}% match`}>⚡ {frag.match_score}%</div>
      </div>
      <div className="frag-list-body">
        <p className="frag-list-brand">{frag.brand || 'Unknown Brand'}</p>
        <h3 className="frag-list-name">{frag.name}</h3>
        {topNotes.length > 0 && (
          <div className="frag-notes-row">
            {topNotes.map((n: string) => <span key={n} className="note-pill note-pill-top">{n}</span>)}
            {midNotes.map((n: string) => <span key={n} className="note-pill note-pill-heart">{n}</span>)}
            {baseNotes.map((n: string) => <span key={n} className="note-pill note-pill-base">{n}</span>)}
          </div>
        )}
        {accords.length > 0 && (
          <div className="frag-accords-row">
            {accords.map((a: string) => <span key={a} className="accord-badge">{a}</span>)}
          </div>
        )}
        <div className="frag-list-footer">
          <div className="frag-rating" aria-label={`Rated ${frag.rating}`}>
            <span className="star">★</span>
            <span className="frag-rating-value">{frag.rating?.toFixed(1)}</span>
          </div>
          <button className="frag-view-btn btn btn-primary" onClick={(e) => { e.stopPropagation(); onClick(); }} aria-label={`View ${frag.name}`}>View →</button>
        </div>
      </div>
    </article>
  );
}
