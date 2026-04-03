'use client';

import { useRouter } from 'next/navigation';

export function FinalCTA() {
  const router = useRouter();

  return (
    <section className="final-cta scroll-reveal">
      <div className="final-cta-container">
        <h2 className="cta-title">Ready to Find Your Perfect Scent?</h2>
        <p className="cta-subtitle">Join thousands discovering fragrances they love</p>

        <button 
          className="cta-button"
          onClick={() => router.push('/onboarding/quiz')}
        >
          Start the Quiz Now
        </button>

        <div className="trust-badges">
          <div className="trust-badge">
            <span className="badge-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </span>
            <span className="badge-text">100% Authentic Fragrances</span>
          </div>
          <div className="trust-badge">
            <span className="badge-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </span>
            <span className="badge-text">GDPR Compliant</span>
          </div>
          <div className="trust-badge">
            <span className="badge-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </span>
            <span className="badge-text">Free US Shipping</span>
          </div>
          <div className="trust-badge">
            <span className="badge-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </span>
            <span className="badge-text">Cancel Anytime</span>
          </div>
        </div>
      </div>
    </section>
  );
}
