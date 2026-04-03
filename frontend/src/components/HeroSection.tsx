'use client';

import React, { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

/* ── HeroSection ── */
export function HeroSection() {
  const router = useRouter();
  const titleRef = useRef<HTMLHeadingElement>(null);

  // Cascade stagger animation on mount
  useEffect(() => {
    const el = titleRef.current;
    if (!el) return;
    el.querySelectorAll<HTMLElement>('.cascade-word').forEach((word, i) => {
      word.style.animationDelay = `${0.15 + i * 0.12}s`;
      word.classList.add('cascade-animate');
    });
  }, []);

  return (
    <section className="hero-section constellation-bg">
      <div className="hero-gradient" aria-hidden="true" />

      <div className="hero-container">
        <div className="hero-content">

          {/* Eyebrow */}
          <p className="hero-eyebrow scroll-reveal">
            <span aria-hidden="true"
              className="eyebrow-emoji super-magnetic-element"
              string="magnetic"
              string-radius="120"
              string-strength="0.16"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z"/></svg>
            </span>
            AI-Powered Fragrance Discovery
            <span aria-hidden="true"
              className="eyebrow-emoji super-magnetic-element"
              string="magnetic"
              string-radius="120"
              string-strength="0.16"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z"/></svg>
            </span>
          </p>

          {/* Cascading headline */}
          <h1 className="hero-title scroll-reveal" ref={titleRef}>
            {['Sculpted', 'by', 'intelligence.'].map((w, i) => (
              <React.Fragment key={i}>
                <span className="cascade-word cascade-plain">{w}</span>
                {' '}
              </React.Fragment>
            ))}
            <br />
            {['Worn', 'by', 'instinct.'].map((w, i) => (
              <React.Fragment key={i}>
                <span className={`cascade-word cascade-gradient instinct-text ${w === 'instinct.' ? 'instinct-mega-glow' : ''}`}>{w}</span>
                {i < 2 ? ' ' : ''}
              </React.Fragment>
            ))}
          </h1>

          {/* Subtitle */}
          <p className="hero-subtitle scroll-reveal">
            Personalized fragrance recommendations.
          </p>

          {/* CTA Buttons — low magnetic sensitivity */}
          <div className="hero-buttons scroll-reveal">
            <button
              id="hero-cta-primary"
              className="btn btn-primary magnetic-element"
              onClick={() => router.push('/onboarding/quiz')}
              string="magnetic"
              string-radius="500"
              string-strength="0.06"
              aria-label="Start fragrance discovery quiz"
            >
              <span
                className="btn-emoji super-magnetic-element"
                string="magnetic"
                string-radius="80"
                string-strength="0.18"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.5 1.86 9.32a7 7 0 0 1-9.86 8.68Z"/><path d="M2 20s.5-1 2-1.5"/></svg>
              </span>
              Start Discovery →
            </button>
            <button
              id="hero-cta-secondary"
              className="btn btn-outline magnetic-element"
              onClick={() => router.push('/fragrances')}
              string="magnetic"
              string-radius="500"
              string-strength="0.06"
              aria-label="Browse fragrance collection"
            >
              <span
                className="btn-emoji super-magnetic-element"
                string="magnetic"
                string-radius="80"
                string-strength="0.18"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>
              </span>
              Browse Fragrances
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="trust-indicators scroll-reveal">
            {[
              { value: '1,000+', label: 'Fragrances', icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v2"/><path d="M6 12a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v8a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-8Z"/><path d="M9 11v11"/><path d="M15 11v11"/></svg> },
              { value: '91.5%', label: 'Match Rate', icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="m10 10 4 4"/><path d="m14 10-4 4"/></svg> },
              { value: '50K+', label: 'Collectors', icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 4s0 2 1 2 2-1 2-1h14s1 0 2 1 1 2 1 2"/><path d="M4 6v13a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6"/></svg> },
            ].map((item) => (
              <div key={item.label} className="indicator">
                <span className="indicator-emoji">{item.icon}</span>
                <span className="indicator-value">{item.value}</span>
                <span className="indicator-label">{item.label}</span>
              </div>
            ))}
          </div>

        </div>
      </div>

      {/* Scroll hint */}
      <div aria-hidden="true" className="scroll-hint">
        <span className="scroll-text">Scroll</span>
        <div className="scroll-line" />
      </div>
    </section>
  );
}


/* ── SocialProofSection (Testimonials) ── */
export function SocialProofSection() {
  const testimonials = [
    {
      id: 1,
      name: 'Elena Rodriguez',
      role: 'Fragrance Collector',
      avatar: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
      text: 'Finally found a tool that understands nuance. The recommendations are eerily accurate — it found my signature scent in minutes.',
      rating: 5,
    },
    {
      id: 2,
      name: 'Marcus Chen',
      role: 'Casual Buyer',
      avatar: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
      text: 'Saved me so much money by helping me understand what I actually like in scents. No more blind purchases.',
      rating: 5,
    },
    {
      id: 3,
      name: 'Sophie Nolan',
      role: 'Perfume Enthusiast',
      avatar: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
      text: 'The AI recommendations introduced me to indie brands I never would have discovered. The constellation graph is stunning.',
      rating: 5,
    },
  ];

  return (
    <section className="social-proof-section">
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-12)' }}>
          <h2
            className="section-title"
            string="split"
            string-split="word"
          >
            Trusted by Fragrance Lovers
          </h2>
          <p className="section-subtitle" style={{ margin: '0 auto' }}>
            See what collectors are saying about their scent discoveries
          </p>
        </div>

        <div className="testimonials-grid">
          {testimonials.map((t) => (
            <div key={t.id} className="testimonial-card glass-card scroll-reveal">
              <div className="testimonial-header">
                <div className="avatar">{t.avatar}</div>
                <div className="author-info">
                  <h3 className="author-name">{t.name}</h3>
                  <p className="author-role">{t.role}</p>
                </div>
              </div>
              <div className="stars" aria-label={`${t.rating} stars`}>
                {Array.from({ length: t.rating }).map((_, i) => (
                  <span key={i} className="star">★</span>
                ))}
              </div>
              <p className="testimonial-text">"{t.text}"</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}


/* ── FeatureSection ── */
export function FeatureSection() {
  const features = [
    {
      icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.5 1.86 9.32a7 7 0 0 1-9.86 8.68Z"/><path d="M2 20s.5-1 2-1.5"/></svg>,
      title: 'Personalized Matching',
      description: 'Graph neural networks analyze your taste profile to surface fragrances tuned exactly to you.',
    },
    {
      icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>,
      title: 'Deep Note Analysis',
      description: 'Detailed breakdowns of top, heart, and base notes with accord mapping and longevity data.',
    },
    {
      icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>,
      title: 'Text-Based Search',
      description: 'Type "smoky vanilla with leather" and our AI finds matching fragrances instantly.',
    },
    {
      icon: <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z"/></svg>,
      title: 'Taste Constellation',
      description: 'Visualize your scent preferences as a beautiful network graph of notes and accords.',
    },
  ];

  return (
    <section className="feature-section">
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-12)' }}>
          <h2
            className="section-title"
            string="split"
            string-split="word"
          >
            Why ScentScape
          </h2>
        </div>

        <div className="features-grid">
          {features.map((f, i) => (
            <div
              key={i}
              className="feature-card"
              string="reveal"
              string-reveal-delay={String(i * 100)}
            >
              <span
                className="feature-icon super-magnetic-element"
                string="magnetic"
                string-radius="100"
                string-strength="0.3"
              >
                {f.icon}
              </span>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-description">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
