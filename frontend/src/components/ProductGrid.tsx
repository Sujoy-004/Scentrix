'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { api, type FragranceCatalogItem } from '@/lib/api';

const BOTTLE_GLOWS = [
  { glow: 'rgba(139,94,60,0.45)',  accent: '#c87941' },
  { glow: 'rgba(176,130,30,0.40)', accent: '#e4c285' },
  { glow: 'rgba(34,90,34,0.35)',   accent: '#76c576' },
  { glow: 'rgba(80,60,40,0.45)',   accent: '#a0785a' },
  { glow: 'rgba(120,30,90,0.35)',  accent: '#e080c0' },
  { glow: 'rgba(30,70,120,0.35)',  accent: '#60a0d9' },
];

const STATIC_METRICS = [
  { rating: 4.8, reviews: 342, match: 89 },
  { rating: 4.9, reviews: 856, match: 92 },
  { rating: 4.7, reviews: 621, match: 85 },
  { rating: 4.8, reviews: 504, match: 91 },
  { rating: 4.6, reviews: 418, match: 87 },
  { rating: 4.7, reviews: 533, match: 88 },
];

export function ProductGrid() {
  const router = useRouter();
  const gridRef = useRef<HTMLDivElement>(null);
  const [items, setItems] = useState<FragranceCatalogItem[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getFragranceCatalog(6, 0);
        setItems(Array.isArray(data?.items) ? data.items.slice(0, 6) : []);
      } catch {
        setItems([]);
      }
    };
    void load();
  }, []);

  const fragrances = items.map((frag, idx) => ({
    id: frag.id,
    brand: frag.brand,
    name: frag.name,
    notes: frag.top_notes?.slice(0, 3) || [],
    family: frag.family || 'parfum',
    rating: STATIC_METRICS[idx]?.rating || 4.5,
    reviews: STATIC_METRICS[idx]?.reviews || 300,
    match: STATIC_METRICS[idx]?.match || 80,
    ...BOTTLE_GLOWS[idx % BOTTLE_GLOWS.length],
  }));

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries, obs) => entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add('cloud-card--visible'); obs.unobserve(e.target); }
      }),
      { threshold: 0.12, rootMargin: '0px 0px -10% 0px' }
    );
    gridRef.current?.querySelectorAll('.cloud-card').forEach((c) => observer.observe(c));
    return () => observer.disconnect();
  }, [fragrances.length]);

  return (
    <section className="product-grid-section">
      <div className="product-grid-container">
        <div className="section-header">
          <h2 className="section-title">Discover Premium Fragrances</h2>
          <p className="section-subtitle" style={{ margin: '0 auto' }}>Handpicked from the world's finest houses</p>
        </div>

        <div className="pg-matrix" ref={gridRef}>
          {fragrances.map((frag, idx) => (
            <div
              key={frag.id}
              className="cloud-card"
              style={{ '--glow-color': frag.glow, '--accent-color': frag.accent, animationDelay: `${idx * 0.08}s` } as React.CSSProperties}
              onClick={() => router.push(`/fragrances/${frag.id}`)}
            >
              <div className="cloud-glow" aria-hidden="true" />
              <div className="cloud-bottle-wrap">
                <div className="cloud-mist" aria-hidden="true" />
                <div className="cloud-bottle-img">
                  <Image
                    src="/perfume-grid.png"
                    alt={`${frag.name} bottle`}
                    width={120}
                    height={140}
                    style={{ objectFit: 'contain', objectPosition: 'center', filter: `drop-shadow(0 8px 20px ${frag.glow})` }}
                    priority={idx < 3}
                  />
                </div>
                <div className="cloud-reflection" aria-hidden="true" />
              </div>
              <div className="cloud-match-badge" style={{ background: `linear-gradient(135deg, ${frag.accent}33, ${frag.accent}22)`, borderColor: `${frag.accent}44` }}>
                {frag.match}% Match
              </div>
              <div className="cloud-body">
                <p className="cloud-brand">{frag.brand}</p>
                <h3 className="cloud-name">{frag.name}</h3>
                <div className="cloud-notes">
                  {frag.notes.map((n: string) => <span key={n} className="note-pill note-pill-top">{n}</span>)}
                </div>
                <div className="cloud-footer">
                  <div className="cloud-rating">
                    <span className="cloud-stars">{'★'.repeat(Math.floor(frag.rating))}</span>
                    <span className="cloud-reviews">({frag.reviews})</span>
                  </div>
                  <button
                    className="cloud-btn"
                    style={{ borderColor: `${frag.accent}55`, color: frag.accent }}
                    onClick={(e) => { e.stopPropagation(); router.push(`/fragrances/${frag.id}`); }}
                  >
                    View →
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
