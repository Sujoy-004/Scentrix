'use client';

import React, { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import './detail.css';

interface FragranceNote {
  id: string;
  name: string;
  category: string;
  intensity?: number;
}

interface FragranceAccord {
  id: string;
  name: string;
  certainty?: number;
}

interface FragranceDetailData {
  id: string;
  name: string;
  brand: string;
  year?: number | null;
  concentration?: string;
  gender_label?: string;
  description?: string;
  top_notes?: FragranceNote[];
  middle_notes?: FragranceNote[];
  base_notes?: FragranceNote[];
  accords?: FragranceAccord[];
}

export default function FragranceDetailPage({ params: paramsPromise }: { params: Promise<{ id: string }> }) {
  const params = use(paramsPromise);
  const [fragrance, setFragrance] = useState<FragranceDetailData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data } = await api.get(`/fragrances/${params.id}`);
        setFragrance(data?.data ?? null);
      } catch {
        setError('Unable to load this fragrance. It may have been removed.');
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, [params.id]);

  if (isLoading) {
    return (
      <div className="fragrance-detail-page">
        <div className="fragrances-loading">
          <div className="loading-spinner">
            <p>Loading fragrance...</p>
            <div className="spinner" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !fragrance) {
    return (
      <div className="fragrance-detail-page">
        <div className="fragrances-error">
          <h2>Unable to load fragrance</h2>
          <p>{error || 'Fragrance not found.'}</p>
          <Link className="error-button" href="/fragrances">
            Back to All Fragrances
          </Link>
        </div>
      </div>
    );
  }

  const noteSections = [
    { label: 'Top Notes', notes: fragrance.top_notes ?? [] },
    { label: 'Middle Notes', notes: fragrance.middle_notes ?? [] },
    { label: 'Base Notes', notes: fragrance.base_notes ?? [] },
  ];

  return (
    <div className="fragrance-detail-page">
      <div className="fragrance-detail-container">
        <div className="fragrances-header">
          <div>
            <h1>{fragrance.name}</h1>
            <p className="detail-brand">{fragrance.brand}</p>
          </div>
          <Link className="back-to-home" href="/fragrances">
            ← All Fragrances
          </Link>
        </div>

        <div className="detail-hero">
          <div className="detail-emoji">🧴</div>
          <div className="detail-meta">
            {fragrance.year && (
              <span className="detail-meta-item">Year: {fragrance.year}</span>
            )}
            <span className="detail-meta-item">Concentration: {fragrance.concentration || 'N/A'}</span>
            <span className="detail-meta-item">Gender: {fragrance.gender_label || 'N/A'}</span>
          </div>
        </div>

        {fragrance.description && (
          <div className="detail-section">
            <h2 className="section-title">Description</h2>
            <p className="detail-description">{fragrance.description}</p>
          </div>
        )}

        <div className="detail-notes-grid">
          {noteSections.map((section) => (
            <div key={section.label} className="detail-section">
              <h2 className="section-title">{section.label}</h2>
              {section.notes.length > 0 ? (
                <div className="notes-pills">
                  {section.notes.map((note) => (
                    <span key={note.id || note.name} className="note-pill">
                      {note.name}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="detail-empty">No {section.label.toLowerCase()} available.</p>
              )}
            </div>
          ))}
        </div>

        <div className="detail-section">
          <h2 className="section-title">Accords</h2>
          {fragrance.accords && fragrance.accords.length > 0 ? (
            <div className="notes-pills">
              {fragrance.accords.map((accord) => (
                <span key={accord.id || accord.name} className="accord-pill">
                  {accord.name}
                </span>
              ))}
            </div>
          ) : (
            <p className="detail-empty">No accords available.</p>
          )}
        </div>

        <div className="detail-footer">
          <Link className="explore-btn" href="/fragrances">
            ← Back to All Fragrances
          </Link>
        </div>
      </div>
    </div>
  );
}
