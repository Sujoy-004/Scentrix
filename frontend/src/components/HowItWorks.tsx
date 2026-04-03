export function HowItWorks() {

  return (
    <section className="how-it-works scroll-reveal">
      <div className="how-it-works-container">
        <div className="how-it-works-header">
          <h2 className="section-title">How It Works</h2>
          <p className="section-subtitle">Discover your perfect fragrance in three simple steps</p>
        </div>

        <div className="steps-grid">
          <div className="step-card step-1 scroll-reveal" style={{ animationDelay: "0.2s", textAlign: 'center' }} string="reveal">
            <div className="step-number" style={{ left: '50%', transform: 'translateX(-50%)' }}>1</div>
            <div className="step-emoji" style={{ margin: '0 auto' }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            </div>
            <h3 className="step-heading" string="split" string-split="char">Rate Your Favorites</h3>
            <p className="step-description">
              Answer quick questions about your favorite fragrances. Rate them on sweetness, woodiness, longevity, and intensity.
            </p>
            <div className="step-visual" style={{ margin: '20px auto 0' }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
            </div>
          </div>

          <div className="step-card step-2 scroll-reveal" style={{ animationDelay: "0.4s", textAlign: 'center' }} string="reveal">
            <div className="step-number" style={{ left: '50%', transform: 'translateX(-50%)' }}>2</div>
            <div className="step-emoji" style={{ margin: '0 auto' }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 4.5V11m0 0 5-2.5m-5 2.5-5-2.5M12 11v8.5m-3-13h6a3 3 0 0 1 3 3v4a5 5 0 0 1-5 5h-2a5 5 0 0 1-5-5v-4a3 3 0 0 1 3-3Z"/></svg>
            </div>
            <h3 className="step-heading" string="split" string-split="char">Get AI-Matched</h3>
            <p className="step-description">
              Our GraphSAGE AI analyzes your taste profile and compares it with 1000+ fragrances from our carefully curated database.
            </p>
            <div className="step-visual" style={{ margin: '20px auto 0' }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/></svg>
            </div>
          </div>

          <div className="step-card step-3 scroll-reveal" style={{ animationDelay: "0.6s", textAlign: 'center' }} string="reveal">
            <div className="step-number" style={{ left: '50%', transform: 'translateX(-50%)' }}>3</div>
            <div className="step-emoji" style={{ margin: '0 auto' }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
            </div>
            <h3 className="step-heading" string="split" string-split="char">Explore & Discover</h3>
            <p className="step-description">
              Browse personalized matches, view detailed notes, read community reviews, and save your favorites to your collection.
            </p>
            <div className="step-visual" style={{ margin: '20px auto 0' }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}



