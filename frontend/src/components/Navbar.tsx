'use client';

import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import { useEffect, useState } from 'react';
import './navbar.css';

export default function Navbar() {
  const router = useRouter();
  const { isAuthenticated, userId, logout } = useAppStore();
  const [isClientSide, setIsClientSide] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  // Prevent hydration mismatch
  useEffect(() => {
    setIsClientSide(true);
  }, []);

  if (!isClientSide) {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo/Brand */}
        <div className="navbar-brand">
          <button
            className="navbar-logo"
            onClick={() => router.push('/')}
          >
            <span className="logo-icon">🌿</span>
            <span className="logo-text">ScentScape</span>
          </button>
        </div>

        {/* Hamburger Menu */}
        <button
          className={`navbar-toggle ${isOpen ? 'active' : ''}`}
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Toggle navigation menu"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>

        {/* Navigation Links */}
        <div className={`navbar-menu ${isOpen ? 'active' : ''}`}>
          <div className="navbar-links">
            {/* Public Links */}
            <button
              className="nav-link"
              onClick={() => {
                router.push('/fragrances');
                setIsOpen(false);
              }}
            >
              Browse
            </button>

            {!isAuthenticated && (
              <>
                <button
                  className="nav-link"
                  onClick={() => {
                    router.push('/auth/login');
                    setIsOpen(false);
                  }}
                >
                  Log In
                </button>
                <button
                  className="nav-link nav-cta"
                  onClick={() => {
                    router.push('/auth/register');
                    setIsOpen(false);
                  }}
                >
                  Sign Up
                </button>
              </>
            )}

            {isAuthenticated && (
              <>
                <button
                  className="nav-link"
                  onClick={() => {
                    router.push('/onboarding/quiz');
                    setIsOpen(false);
                  }}
                >
                  Quiz
                </button>
                <button
                  className="nav-link"
                  onClick={() => {
                    router.push('/recommendations');
                    setIsOpen(false);
                  }}
                >
                  Recommendations
                </button>
                <button
                  className="nav-link"
                  onClick={() => {
                    router.push('/profile');
                    setIsOpen(false);
                  }}
                >
                  Profile
                </button>
                <button
                  className="nav-link"
                  onClick={() => {
                    router.push('/profile/wishlist');
                    setIsOpen(false);
                  }}
                >
                  Wishlist
                </button>

                <div className="navbar-divider"></div>

                <button
                  className="nav-link nav-logout"
                  onClick={() => {
                    handleLogout();
                    setIsOpen(false);
                  }}
                >
                  Log Out
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
