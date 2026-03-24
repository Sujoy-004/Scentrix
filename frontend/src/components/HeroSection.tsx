'use client';

import React from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { BackgroundAnimation } from './BackgroundAnimation';

export function HeroSection() {
  const router = useRouter();
  return (
    <section className="hero-section">
      {/* Animated Background Canvas */}
      <BackgroundAnimation />

      {/* Hero Background with Gradient Overlay */}
      <div className="hero-gradient"></div>

      {/* Hero Content */}
      <div className="hero-container">
        <div className="hero-content">
          <h1 className="hero-title">
            Discover Your Perfect Scent
          </h1>
          <p className="hero-subtitle">
            Personalized fragrance recommendations powered by AI. Find the signature scent that speaks to your essence.
          </p>

          <div className="hero-buttons">
            <button 
              className="btn btn-primary"
              onClick={() => router.push('/onboarding/quiz')}
            >
              Start Discovery
            </button>
            <button 
              className="btn btn-outline"
              onClick={() => router.push('/fragrances')}
            >
              Learn More
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="trust-indicators">
            <div className="indicator">
              <span className="indicator-value">98%</span>
              <span className="indicator-label">Match Satisfaction</span>
            </div>
            <div className="indicator">
              <span className="indicator-value">1,000+</span>
              <span className="indicator-label">Fragrance Database</span>
            </div>
            <div className="indicator">
              <span className="indicator-value">50K+</span>
              <span className="indicator-label">Happy Collectors</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function SocialProofSection() {
  const testimonials = [
    {
      id: 1,
      name: 'Elena Rodriguez',
      role: 'Fragrance Collector',
      avatar: '👩‍🦱',
      text: '"Finally found a tool that understands nuance. The recommendations are eerily accurate."',
      rating: 5,
    },
    {
      id: 2,
      name: 'Marcus Chen',
      role: 'Casual Buyer',
      avatar: '👨‍💼',
      text: '"Saved me so much money by helping me understand what I actually like in scents."',
      rating: 5,
    },
    {
      id: 3,
      name: 'Sophie Nolan',
      role: 'Perfume Enthusiast',
      avatar: '👩‍🎨',
      text: '"The AI recommendations introduced me to indie brands I never would have found."',
      rating: 5,
    },
  ];

  return (
    <section className="social-proof-section">
      <div className="container">
        <h2 className="section-title">Trusted by Fragrance Lovers</h2>
        <p className="section-subtitle">
          See what people are saying about their scent discoveries
        </p>

        <div className="testimonials-grid">
          {testimonials.map((testimonial) => (
            <div key={testimonial.id} className="testimonial-card">
              <div className="testimonial-header">
                <div className="avatar">{testimonial.avatar}</div>
                <div className="author-info">
                  <h3 className="author-name">{testimonial.name}</h3>
                  <p className="author-role">{testimonial.role}</p>
                </div>
              </div>

              <p className="testimonial-text">{testimonial.text}</p>

              <div className="stars">
                {[...Array(testimonial.rating)].map((_, i) => (
                  <span key={i} className="star">⭐</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function FeatureSection() {
  const features = [
    {
      icon: '🌿',
      title: 'Personalized Matching',
      description: 'AI analyzes your preferences to find your perfect fragrance match',
    },
    {
      icon: '📊',
      title: 'Expert Analysis',
      description: 'Detailed breakdowns of fragrance notes, accords, and longevity',
    },
    {
      icon: '🔍',
      title: 'Extensive Database',
      description: '1,000+ fragrances from premium to indie and niche brands',
    },
    {
      icon: '💬',
      title: 'Community Insights',
      description: 'Connect with other collectors and share your discoveries',
    },
  ];

  return (
    <section className="feature-section">
      <div className="container">
        <h2 className="section-title">Why Choose ScentScape</h2>

        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-card">
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-description">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
