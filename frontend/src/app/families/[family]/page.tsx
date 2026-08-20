'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, type FragranceCatalogItem } from '@/lib/api';
import { getFamilyBySlug } from '@/lib/families';
import { FragranceCard } from '@/components/FragranceCard';
import '../../recommendations/recommendations.css';
import './family.css';

export default function FamilyPage() {
  const router = useRouter();
  const params = useParams<{ family: string }>();
  const slug = (params?.family ?? '').toLowerCase();
  const family = getFamilyBySlug(slug);

  const [items, setItems] = useState<FragranceCatalogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getFragranceCatalog(200, 0, { family: slug })
      .then((result) => {
        if (cancelled) return;
        setItems(result?.data?.items ?? result?.items ?? []);
        setTotal(result?.data?.total ?? result?.total ?? 0);
      })
      .catch(() => {
        if (cancelled) return;
        setError('We could not load fragrances for this family. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug, family]);

  if (!family) {
    return (
      <div className="family-page">
        <div className="family-state">
          <p className="family-state-eyebrow">Unknown Family</p>
          <h1 className="family-state-title">Family not found</h1>
          <p className="family-state-text">The family &quot;{slug || params?.family}&quot; does not exist in our collection.</p>
          <button className="family-back-btn" onClick={() => router.push('/families')}>
            ← All Families
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="family-page">
        <div className="family-loader">
          <span className="family-loader-spinner" />
          <p>Loading {family.name} fragrances…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="family-page">
        <div className="family-state">
          <p className="family-state-eyebrow">Error</p>
          <h1 className="family-state-title">Something went wrong</h1>
          <p className="family-state-text">{error}</p>
          <div className="family-state-actions">
            <button
              className="family-back-btn"
              onClick={() => {
                setLoading(true);
                setError(null);
                api
                  .getFragranceCatalog(200, 0, { family: slug })
                  .then((result) => {
                    setItems(result?.data?.items ?? result?.items ?? []);
                    setTotal(result?.data?.total ?? result?.total ?? 0);
                  })
                  .catch(() => setError('We could not load fragrances for this family. Please try again.'))
                  .finally(() => setLoading(false));
              }}
            >
              Retry
            </button>
            <button className="family-back-btn family-back-btn-ghost" onClick={() => router.push('/families')}>
              ← All Families
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="family-page">
      <div className="family-header">
        <button className="family-back-link" onClick={() => router.push('/families')}>
          ← All Families
        </button>
        <p className="family-eyebrow">{family.tagline}</p>
        <h1 className="family-title">{family.name}</h1>
        <p className="family-description">{family.description}</p>
        <p className="family-count">
          {total.toLocaleString()} {total === 1 ? 'fragrance' : 'fragrances'} in this family
        </p>
      </div>

      {items.length === 0 ? (
        <div className="family-state">
          <h1 className="family-state-title">No fragrances found</h1>
          <p className="family-state-text">We couldn&apos;t find any fragrances in this family yet.</p>
          <button className="family-back-btn" onClick={() => router.push('/families')}>
            ← All Families
          </button>
        </div>
      ) : (
        <>
          <div className="recommendations-grid-elite">
            {items.map((frag, i) => (
              <FragranceCard key={frag.id} frag={frag} index={i} showMatch={false} />
            ))}
          </div>
          {total > items.length && (
            <p className="family-truncation-note">
              Showing first {items.length} of {total.toLocaleString()} — refine your search to narrow results.
            </p>
          )}
        </>
      )}
    </div>
  );
}
