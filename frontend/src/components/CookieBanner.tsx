'use client';

import { useState, useEffect } from 'react';

const COOKIE_KEY = 'scentscape_cookie_consent';

type ConsentState = 'accepted' | 'declined' | 'customized' | null;

export default function CookieBanner() {
  const [visible, setVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [analytics, setAnalytics] = useState(true);
  const [marketing, setMarketing] = useState(false);

  useEffect(() => {
    // Only show if no decision has been stored
    const stored = localStorage.getItem(COOKIE_KEY);
    if (!stored) {
      // Delay slightly so the rest of the page renders first
      const t = setTimeout(() => setVisible(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  const save = (state: ConsentState, prefs?: { analytics: boolean; marketing: boolean }) => {
    localStorage.setItem(COOKIE_KEY, JSON.stringify({ state, timestamp: Date.now(), prefs }));
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Cookie consent banner"
      id="cookie-consent-banner"
      style={{
        position: 'fixed',
        bottom: '24px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9000,
        width: 'min(95vw, 640px)',
        background: 'rgba(26, 23, 20, 0.97)',
        border: '1px solid rgba(244, 187, 146, 0.14)',
        borderRadius: '20px',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        boxShadow: '0 24px 64px rgba(0,0,0,0.6), 0 0 0 1px rgba(244,187,146,0.04)',
        padding: '24px',
        fontFamily: 'var(--font-body), serif',
        animation: 'slideUpIn 0.5s cubic-bezier(0.86,0,0.31,1) both',
      }}
    >
      <style>{`
        @keyframes slideUpIn {
          from { opacity: 0; transform: translateX(-50%) translateY(24px); }
          to   { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        .cookie-toggle-track {
          width: 40px; height: 22px;
          background: rgba(56,52,49,0.8);
          border-radius: 11px;
          position: relative;
          cursor: pointer;
          border: 1px solid rgba(244,187,146,0.15);
          transition: background 0.2s;
        }
        .cookie-toggle-track.on { background: linear-gradient(135deg,#f4bb92,#8b5e3c); }
        .cookie-toggle-thumb {
          position: absolute;
          top: 2px; left: 2px;
          width: 16px; height: 16px;
          background: #fff;
          border-radius: 50%;
          transition: transform 0.2s ease;
          box-shadow: 0 1px 4px rgba(0,0,0,0.4);
        }
        .cookie-toggle-track.on .cookie-toggle-thumb { transform: translateX(18px); }
      `}</style>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <p style={{ margin: 0, fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#f4bb92', marginBottom: '4px' }}>
            ✦ Your Privacy
          </p>
          <h2 style={{ margin: 0, fontFamily: 'Cormorant Garamond, Georgia, serif', fontStyle: 'italic', fontSize: '1.4rem', fontWeight: 400, color: '#e9e1dc', lineHeight: 1.1 }}>
            We use cookies
          </h2>
        </div>
        <button
          onClick={() => save('declined')}
          aria-label="Close and decline cookies"
          style={{ background: 'none', border: 'none', color: '#9e8e84', cursor: 'pointer', fontSize: '1.2rem', padding: '4px', lineHeight: 1, borderRadius: '50%', transition: 'color 0.15s' }}
        >
          ×
        </button>
      </div>

      {/* Body text */}
      <p style={{ margin: '0 0 16px 0', fontSize: '0.85rem', color: '#d5c3b8', lineHeight: 1.65, fontWeight: 300 }}>
        ScentScapeAI uses cookies to power personalized fragrance recommendations, remember your preferences, and improve our AI matching. You can choose which cookies to allow.{' '}
        <a href="/privacy" style={{ color: '#f4bb92', textDecoration: 'underline', textDecorationColor: 'rgba(244,187,146,0.3)' }}>
          Privacy Policy
        </a>
      </p>

      {/* Expandable details */}
      {showDetails && (
        <div style={{
          background: 'rgba(56,52,49,0.3)',
          border: '1px solid rgba(244,187,146,0.06)',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}>
          {/* Essential */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ margin: 0, fontSize: '0.82rem', fontWeight: 600, color: '#e9e1dc' }}>Essential</p>
              <p style={{ margin: '2px 0 0', fontSize: '0.75rem', color: '#9e8e84' }}>Required for core features — always on</p>
            </div>
            <div className="cookie-toggle-track on" aria-label="Essential cookies, always enabled">
              <div className="cookie-toggle-thumb" />
            </div>
          </div>

          {/* Analytics */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ margin: 0, fontSize: '0.82rem', fontWeight: 600, color: '#e9e1dc' }}>Analytics</p>
              <p style={{ margin: '2px 0 0', fontSize: '0.75rem', color: '#9e8e84' }}>Help us understand how fragrances are discovered</p>
            </div>
            <button
              onClick={() => setAnalytics(a => !a)}
              className={`cookie-toggle-track ${analytics ? 'on' : ''}`}
              aria-label={`Analytics cookies ${analytics ? 'enabled' : 'disabled'}`}
              aria-checked={analytics}
              role="switch"
            >
              <div className="cookie-toggle-thumb" />
            </button>
          </div>

          {/* Marketing */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ margin: 0, fontSize: '0.82rem', fontWeight: 600, color: '#e9e1dc' }}>Marketing</p>
              <p style={{ margin: '2px 0 0', fontSize: '0.75rem', color: '#9e8e84' }}>Personalized fragrance ads across the web</p>
            </div>
            <button
              onClick={() => setMarketing(m => !m)}
              className={`cookie-toggle-track ${marketing ? 'on' : ''}`}
              aria-label={`Marketing cookies ${marketing ? 'enabled' : 'disabled'}`}
              aria-checked={marketing}
              role="switch"
            >
              <div className="cookie-toggle-thumb" />
            </button>
          </div>
        </div>
      )}

      {/* Buttons */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <button
          id="cookie-accept-all"
          onClick={() => save('accepted', { analytics: true, marketing: true })}
          style={{
            flex: 1,
            minWidth: '140px',
            padding: '10px 20px',
            background: 'linear-gradient(135deg,#f4bb92,#8b5e3c)',
            color: '#4a280a',
            border: 'none',
            borderRadius: '9999px',
            fontFamily: 'var(--font-body), serif',
            fontSize: '0.78rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            cursor: 'pointer',
            transition: 'all 0.2s',
            boxShadow: '0 4px 16px rgba(244,187,146,0.2)',
          }}
          onMouseEnter={e => (e.currentTarget.style.transform = 'translateY(-1px)')}
          onMouseLeave={e => (e.currentTarget.style.transform = '')}
        >
          Accept All
        </button>

        {showDetails ? (
          <button
            id="cookie-save-prefs"
            onClick={() => save('customized', { analytics, marketing })}
            style={{
              flex: 1,
              minWidth: '140px',
              padding: '10px 20px',
              background: 'transparent',
              color: '#f4bb92',
              border: '1px solid rgba(244,187,146,0.35)',
              borderRadius: '9999px',
              fontFamily: 'var(--font-body), serif',
              fontSize: '0.78rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Save Preferences
          </button>
        ) : (
          <button
            id="cookie-customize"
            onClick={() => setShowDetails(true)}
            style={{
              flex: 1,
              minWidth: '140px',
              padding: '10px 20px',
              background: 'transparent',
              color: '#d5c3b8',
              border: '1px solid rgba(244,187,146,0.12)',
              borderRadius: '9999px',
              fontFamily: 'var(--font-body), serif',
              fontSize: '0.78rem',
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Customize
          </button>
        )}

        <button
          id="cookie-decline"
          onClick={() => save('declined', { analytics: false, marketing: false })}
          style={{
            padding: '10px 16px',
            background: 'transparent',
            color: '#9e8e84',
            border: '1px solid rgba(158,142,132,0.15)',
            borderRadius: '9999px',
            fontFamily: 'var(--font-body), serif',
            fontSize: '0.78rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'color 0.15s',
          }}
        >
          Decline
        </button>
      </div>
    </div>
  );
}
