'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, type FragranceCatalogItem } from '@/lib/api';
import './fragrances.css';

const FAMILIES = ['Floral', 'Woody', 'Citrus', 'Amber', 'Aromatic', 'Fruity', 'Chypré', 'Aquatic'];
const CONCENTRATIONS = ['All', 'EDP', 'EDT', 'Parfum', 'EDC'];
const RATINGS = [4.8, 4.9, 4.7, 4.8, 4.6, 4.7, 4.5, 4.9];
const MATCHES = [89, 92, 85, 91, 87, 88, 80, 90];
const PER_PAGE = 12;

export default function FragrancesPage() {
  const router = useRouter();
  const gridRef = useRef<HTMLDivElement>(null);
  const [allItems, setAllItems] = useState<FragranceCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sortBy, setSortBy] = useState<'rating' | 'name' | 'match'>('rating');
  const [filterFamily, setFilterFamily] = useState('');
  const [filterConc, setFilterConc] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const data = await api.getFragranceCatalog(200, 0);
        setAllItems(Array.isArray(data?.items) ? data.items : []);
      } catch {
        setAllItems([]);
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, []);

  const enriched = allItems.map((f, i) => ({
    ...f,
    rating: RATINGS[i % RATINGS.length],
    match_score: MATCHES[i % MATCHES.length],
  }));

  const filtered = enriched.filter((f) => {
    const matchesFamily = !filterFamily || f.family?.toLowerCase() === filterFamily.toLowerCase();
    const matchesSearch = !searchQuery || (() => {
      const q = searchQuery.toLowerCase();
      return (
        f.name?.toLowerCase().includes(q) ||
        f.brand?.toLowerCase().includes(q) ||
        f.top_notes?.some((n) => n.toLowerCase().includes(q))
      );
    })();
    return matchesFamily && matchesSearch;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === 'rating') return (b.rating as number) - (a.rating as number);
    if (sortBy === 'name') return (a.name || '').localeCompare(b.name || '');
    if (sortBy === 'match') return (b.match_score as number) - (a.match_score as number);
    return 0;
  });

  const totalPages = Math.ceil(sorted.length / PER_PAGE);
  const paginated = sorted.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  useEffect(() => { setPage(1); }, [filterFamily, searchQuery, sortBy]);

  useEffect(() => {
    if (!gridRef.current) return;
    gridRef.current.querySelectorAll('.frag-list-card').forEach((card, i) => {
      (card as HTMLElement).style.animationDelay = `${i * 40}ms`;
      card.classList.add('card-enter');
    });
  }, [paginated.length, page]);

  if (isLoading) {
    return (
      <div className="browse-page">
        <div className="browse-header">
          <div className="browse-header-inner container">
            <p className="browse-eyebrow">✦ Collection</p>
            <h1 className="browse-title">Loading fragrances...</h1>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="browse-page">
      <div className="browse-header">
        <div className="browse-header-inner container">
          <div>
            <p className="browse-eyebrow">✦ Collection</p>
            <h1 className="browse-title">
              Explore <span className="text-gradient-amber">Fragrances</span>
            </h1>
            <p className="browse-subtitle">{sorted.length} fragrances curated for discovery</p>
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
            <p className="sidebar-label">Family</p>
            <div className="family-chip-grid">
              <button className={`family-chip ${filterFamily === '' ? 'active' : ''}`} onClick={() => setFilterFamily('')}>All</button>
              {FAMILIES.map((f) => (
                <button
                  key={f}
                  className={`family-chip ${filterFamily === f.toLowerCase() ? 'active' : ''}`}
                  onClick={() => setFilterFamily(f.toLowerCase())}
                >{f}</button>
              ))}
            </div>
          </div>
          <div className="sidebar-section">
            <p className="sidebar-label">Concentration</p>
            <div className="family-chip-grid">
              {CONCENTRATIONS.map((c) => (
                <button key={c} className={`family-chip ${filterConc === c ? 'active' : ''}`} onClick={() => setFilterConc(c)}>{c}</button>
              ))}
            </div>
          </div>
          <div className="sidebar-section">
            <p className="sidebar-label">Sort By</p>
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
            <span className="result-count">Showing <strong>{paginated.length}</strong> of {sorted.length}</span>
            <div className="toolbar-sort-mobile">
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)} className="sort-select-mobile" aria-label="Sort fragrances">
                <option value="rating">Highest Rated</option>
                <option value="match">Best Match</option>
                <option value="name">A–Z Name</option>
              </select>
            </div>
          </div>

          {paginated.length === 0 ? (
            <div className="empty-state">
              <p style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontStyle: 'italic', color: 'var(--color-on-surface-var)' }}>No fragrances found</p>
              <p style={{ color: 'var(--color-muted)', marginTop: '8px' }}>Try adjusting your search or filters</p>
              <button className="btn btn-outline" style={{ marginTop: '24px' }} onClick={() => { setFilterFamily(''); setSearchQuery(''); }}>Clear All</button>
            </div>
          ) : (
            <div className="fragrances-grid" ref={gridRef}>
              {paginated.map((frag, idx) => (
                <FragCard key={frag.id || idx} frag={frag} index={idx} onClick={() => router.push(`/fragrances/${frag.id || `frag-${idx}`}`)} />
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="pagination">
              <button className="page-btn" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} aria-label="Previous page">←</button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button key={p} className={`page-btn ${p === page ? 'active' : ''}`} onClick={() => setPage(p)} aria-label={`Page ${p}`} aria-current={p === page ? 'page' : undefined}>{p}</button>
              ))}
              <button className="page-btn" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} aria-label="Next page">→</button>
            </div>
          )}
        </main>
      </div>
    </div>
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
