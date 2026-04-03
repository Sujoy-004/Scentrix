'use client';

export function SocialProof() {

  const testimonials = [
    {
      name: 'Sarah M.',
      rating: 5,
      text: 'Finally found a fragrance that matches my personality perfectly. The AI recommendations are incredibly accurate!',
      match: '92% Match',
    },
    {
      name: 'James L.',
      rating: 5,
      text: 'Best discovery platform for fragrances. I\'ve found three new signatures in just a month.',
      match: '88% Match',
    },
    {
      name: 'Emma R.',
      rating: 5,
      text: 'Love the community ratings and detailed notes breakdowns. Makes choosing so much easier.',
      match: '95% Match',
    },
  ];

  return (
    <section className="social-proof section">
      <div className="social-proof-container">
        <div className="section-header">
          <h2 className="section-title">Loved by Fragrance Enthusiasts</h2>
        </div>

        <div className="stats-row">
          <div className="stat-card reveal-cascade">
            <div className="stat-icon-premium">
               <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M6 3h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M8 7h8"/><path d="M10 11h4"/><path d="M12 15h0"/></svg>
            </div>
            <div className="stat-number-elite serif">1,500</div>
            <div className="stat-label-elite">Active Users</div>
          </div>

          <div className="stat-card reveal-cascade">
            <div className="stat-icon-premium">
               <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="m16 8-8 8"/><path d="m8 8 8 8"/></svg>
            </div>
            <div className="stat-number-elite serif">91.5%</div>
            <div className="stat-label-elite">Match Satisfaction</div>
          </div>

          <div className="stat-card reveal-cascade">
            <div className="stat-icon-premium">
               <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9Z"/><path d="m3 9 2.45-4.9A2 2 0 0 1 7.24 3h9.52a2 2 0 0 1 1.8 1.1L21 9"/><path d="M12 3v6"/></svg>
            </div>
            <div className="stat-number-elite serif">2k+</div>
            <div className="stat-label-elite">Fragrance Available</div>
          </div>
        </div>

        <div className="testimonials-grid">
          {testimonials.map((testimonial, index) => (
            <div key={index} className="testimonial-card glass-card scroll-reveal">
              <div className="testimonial-glow"></div>
              <div className="testimonial-rating">
                {Array.from({ length: testimonial.rating }).map((_, i) => (
                  <svg key={i} width="14" height="14" viewBox="0 0 24 24" fill="var(--amber-glow)" style={{ opacity: 0.8 }}>
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                ))}
              </div>
              <p className="testimonial-text">"{testimonial.text}"</p>
              <div className="testimonial-footer">
                <div className="testimonial-info">
                  <span className="testimonial-name">{testimonial.name}</span>
                  <span className="testimonial-badge">{testimonial.match}</span>
                </div>
              </div>
              <div className="testimonial-sheen"></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
