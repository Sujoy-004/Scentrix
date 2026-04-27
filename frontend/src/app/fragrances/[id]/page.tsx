'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import { VideoScrubber } from '@/components/VideoScrubber';
import { DiscoveryNeuralLoader } from '@/components/DiscoveryNeuralLoader';
import './fragrance-detail.css';

type FragranceNotePayload = { name?: string } | string;

type FragranceDetailPayload = {
  id: string;
  brand: string;
  name: string;
  family?: string;
  price?: number;
  rating?: number;
  review_count?: number;
  match_score?: number;
  longevity?: string;
  fragrance_type?: string;
  sillage?: string;
  recommendation?: string;
  top_notes?: FragranceNotePayload[];
  middle_notes?: FragranceNotePayload[];
  base_notes?: FragranceNotePayload[];
  accords?: Array<{ name?: string } | string>;
  concentration?: string;
  description?: string;
  image_url?: string;
  year?: number | string;
  similarity_score?: number;
};


function normalizeNotes(notes: FragranceNotePayload[] | undefined, fallback: string[]): string[] {
  const values = (notes || [])
    .map((note) => (typeof note === 'string' ? note : note?.name || ''))
    .filter((note): note is string => !!note);
  return values.length > 0 ? values : fallback;
}

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

function BottleVisual({ id, color }: { id: string; color?: string }) {
  const finalColor = color || BOTTLE_COLORS[id] || BOTTLE_COLORS[parseInt(id) % 8 || 1] || 'linear-gradient(135deg, #f4bb92, #e4c285)';
  return (
    <div className="dna-core-visual-detail">
      <div className="dna-core-pulse-aura-detail" style={{ background: finalColor }} />
      <div className="dna-core-glass-detail" style={{ background: finalColor }}>
        <div className="dna-liquid-glow-detail" />
        <div className="dna-rim-highlight-detail" />
        <div className="dna-center-particle-detail" />
      </div>
      <div className="dna-label-tag-detail">ELITE FRAGMENT DNA</div>
    </div>
  );
}

export default function FragranceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id || '';
  const sectionRef = useRef<HTMLDivElement>(null);
  const [fragrance, setFragrance] = useState<FragranceDetailPayload | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const { addToWishlist } = useAppStore();

  useEffect(() => {
    const controller = new AbortController();
    const apiBase = process.env.NEXT_PUBLIC_API_URL;
    if (!apiBase) {
      console.error("NEXT_PUBLIC_API_URL is not defined");
      setLoadError("System configuration error: API base not defined.");
      setIsLoading(false);
      return;
    }

    const loadFragrance = async () => {
      if (!id) {
        setFragrance(null);
        setIsLoading(false);
        setLoadError('Invalid fragrance id');
        return;
      }

      setIsLoading(true);
      setLoadError('');
      try {
        const response = await fetch(`${apiBase}/fragrances/${id}`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Fragrance fetch failed (${response.status})`);
        }
        const payload = (await response.json()) as FragranceDetailPayload;
        setFragrance(payload);
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          return;
        }
        console.error('Failed to load fragrance detail:', error);
        setFragrance(null);
        setLoadError('We could not load this fragrance profile right now.');
      } finally {
        setIsLoading(false);
      }
    };

    void loadFragrance();

    return () => {
      controller.abort();
    };
  }, [id]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && e.target.classList.add('animate-fade-in')),
      { threshold: 0.08 }
    );
    if (sectionRef.current) {
      observer.observe(sectionRef.current);
      sectionRef.current.querySelectorAll('.detail-card,.review-card,.pyramid-level')
        .forEach((el: Element) => observer.observe(el));
    }
    return () => observer.disconnect();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <DiscoveryNeuralLoader />
      </div>
    );
  }

  if (!fragrance) {
    return (
      <div className="detail-error min-h-screen bg-black">
        <div className="error-inner">
          <span className="error-icon">🔍</span>
          <h2 className="text-white">Fragrance not found</h2>
          <p className="text-white/60">{loadError || 'We could not find the requested fragrance.'}</p>
          <button className="error-button" onClick={() => router.push('/fragrances')}>
            ← Back to All Fragrances
          </button>
        </div>
      </div>
    );
  }

  const notePyramid = {
    top: normalizeNotes(fragrance.top_notes, ['Bergamot', 'Lemon']),
    middle: normalizeNotes(fragrance.middle_notes, ['Jasmine', 'Rose']),
    base: normalizeNotes(fragrance.base_notes, ['Sandalwood', 'Musk']),
  };

  const mainAccord = fragrance.family || 'Unknown';

  const accordColors: Record<string, string> = {
    Citrus: 'rgba(184, 134, 11, 0.15)',
    Floral: 'rgba(139, 26, 74, 0.15)',
    Woody: 'rgba(59, 44, 36, 0.15)',
    Oriental: 'rgba(90, 42, 27, 0.15)',
    Fresh: 'rgba(120, 200, 255, 0.15)',
    Green: 'rgba(15, 61, 46, 0.15)',
    Musky: 'rgba(74, 74, 74, 0.15)',
    Unknown: 'rgba(244, 187, 146, 0.15)',
  };

  const auraColor = accordColors[mainAccord] || accordColors.Unknown;

  return (
    <div className="fragrance-detail-page" style={{ '--aura-color-1': auraColor } as any}>
      <VideoScrubber 
        videoPath="/assets/top_hero.mp4"
        isFixed={true}
      />
      
      <div className="detail-container" ref={sectionRef}>

        {/* Cinematic Back Action */}
        <button className="back-button" onClick={() => router.back()}>
          ← The Archive
        </button>

        {/* Fragmented Hero Section */}
        <div className="detail-header">
          {/* Aetheric Visual Core */}
          <div className="fragrance-image-section">
            <div className="bottle-showcase">
              {fragrance.image_url ? (
                <img 
                  src={fragrance.image_url} 
                  alt={fragrance.name} 
                  className="detail-bottle-img" 
                  onError={(e) => (e.currentTarget.style.display = 'none')}
                />
              ) : (
                <BottleVisual id={fragrance.id} />
              )}
              <div className="bottle-shadow" />
            </div>
          </div>

          {/* Genetic Specifications */}
          <div className="fragrance-info-section">
            <div className="fragrance-header-info">
              <span className="detail-family-badge">{fragrance.concentration || fragrance.family || 'Neural Essence'}</span>
              <h1 className="fragrance-detail-title">{fragrance.name}</h1>
              <p className="fragrance-detail-brand">{fragrance.brand}</p>
              {fragrance.year && <p className="fragrance-year">Origin Year: {fragrance.year}</p>}
            </div>

            <div className="fragrance-metrics">
              <div className="metric-block">
                <span className="metric-label">Neural Resonance</span>
                <div className="metric-value match-pct">
                  {typeof fragrance.similarity_score === 'number'
                    ? Math.round(fragrance.similarity_score * 100)
                    : ((fragrance.match_score as number) || 87)}%
                </div>
              </div>
              <div className="metric-block">
                <span className="metric-label">Longevity Trace</span>
                <div className="metric-value">{fragrance.longevity || '8–12 hrs'}</div>
              </div>
              <div className="metric-block">
                <span className="metric-label">Market Status</span>
                <div className="metric-value">
                  <span className="stars">{'★'.repeat(Math.floor(fragrance.rating || 4))}</span>
                </div>
              </div>
            </div>

            <p className="fragrance-description">
              "{fragrance.description || 'A sophisticated molecular blend with a complex DNA signature that unfolds beautifully on the skin over time.'}"
            </p>

            <div className="action-buttons-detail">
              <button
                className="btn-primary-detail button-glow-effect"
                onClick={() => { addToWishlist(fragrance.id || id); }}
              >
                Inscribe into Collection
              </button>
              <button
                className="btn-secondary-detail"
                onClick={() => router.push('/recommendations')}
              >
                Genetic Neighbors →
              </button>
            </div>
          </div>
        </div>

        {/* The Sensory Constellation */}
        <div className="note-pyramid-section">
          <h2 className="section-title">The Sensory Genome</h2>
          <div className="pyramid-container">
            {[
              { key: 'top', label: 'The Immediate Pulse', notes: notePyramid.top, desc: 'Top Notes · 0–20 min' },
              { key: 'middle', label: 'The Persistent Heart', notes: notePyramid.middle, desc: 'Soul · 20 min–3 hrs' },
              { key: 'base', label: 'The Lasting Echo', notes: notePyramid.base, desc: 'Base · 4–12 hrs' },
            ].map(({ key, label, notes, desc }) => (
              <div key={key} className={`pyramid-level ${key}-level`}>
                <div className="level-info">
                  <div className="level-label">{label}</div>
                  <div className="level-desc">{desc}</div>
                </div>
                <div className="notes-list">
                  {notes.map((note: string, idx: number) => (
                    <div key={idx} className="note-item">{note}</div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* DNA Details */}
        <div className="details-section">
          <div className="detail-card">
            <h3>Molecular Properties</h3>
            <ul className="detail-list">
              <li><span className="label">Structure:</span><span className="value">{fragrance.fragrance_type || 'Molecular Perfume'}</span></li>
              <li><span className="label">Density:</span><span className="value">{fragrance.concentration || 'Hybrid Essence'}</span></li>
              <li><span className="label">Aura (Sillage):</span><span className="value">{fragrance.sillage || 'Enveloping'}</span></li>
            </ul>
          </div>
          <div className="detail-card">
            <h3>Environment Scan</h3>
            <div className="occasion-tags">
              {['Twilight Wear', 'Noir Events', 'Intimate Study', 'Gilded Evenings'].map(o => (
                <span key={o} className="tag">{o}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Global Feedback Echoes */}
        <div className="reviews-section">
          <h2 className="section-title">Enthusiast Feedback</h2>
          <div className="reviews-grid">
            {[
              { name: 'Elena R.', stars: 5, text: 'A cinematic masterpiece. The opening is fresh, but the dry down is pure silent luxury.', time: '2 days ago' },
              { name: 'Marcus C.', stars: 5, text: 'The AI nailed the woody resonance. This is my new signature pulse.', time: '1 week ago' },
            ].map((r, idx) => (
              <div key={idx} className="review-card">
                <div className="review-header">
                  <span className="reviewer-avatar">S</span>
                  <div className="reviewer-info">
                    <p className="reviewer-name">{r.name}</p>
                    <span className="review-rating">{'★'.repeat(r.stars)}</span>
                  </div>
                  <span className="review-date">{r.time}</span>
                </div>
                <p className="review-text">"{r.text}"</p>
              </div>
            ))}
          </div>
        </div>

        {/* Interaction Core */}
        <div className="detail-footer">
          <button className="footer-btn-primary" onClick={() => router.push('/recommendations')}>
            Analyze My Profile
          </button>
          <button className="footer-btn-secondary" onClick={() => router.push('/fragrances')}>
            Browse Library
          </button>
        </div>
      </div>
    </div>
  );
}
