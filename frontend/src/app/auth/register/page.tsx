'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useRegister } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import '../auth.css';

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const registerMutation = useRegister();
  const { setAuthToken, setUserId } = useAppStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!name || !email || !password || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (name.length < 2) {
      setError('Name must be at least 2 characters');
      return;
    }

    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError('Please enter a valid email address');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!agreeToTerms) {
      setError('You must agree to the Terms of Service and Privacy Policy');
      return;
    }

    setIsLoading(true);

    registerMutation.mutate(
      { email, password, full_name: name },
      {
        onSuccess: (data: any) => {
          setAuthToken(data.access_token);
          if (data.user_id) setUserId(data.user_id);
          router.push('/onboarding/quiz');
        },
        onError: (err: any) => {
          setError(err.response?.data?.detail || 'Registration failed. Please try again.');
          setIsLoading(false);
        },
      }
    );
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <h1>Create Account</h1>
            <p>Join our community of fragrance enthusiasts</p>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label htmlFor="name">Full Name</label>
              <input
                id="name"
                type="text"
                placeholder="Your full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="form-input"
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="form-input"
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <div className="password-wrapper">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="form-input"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="password-toggle"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  disabled={isLoading}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="confirm-password">Confirm Password</label>
              <div className="password-wrapper">
                <input
                  id="confirm-password"
                  type={showConfirm ? 'text' : 'password'}
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="form-input"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="password-toggle"
                  aria-label={showConfirm ? 'Hide password' : 'Show password'}
                  disabled={isLoading}
                  title={showConfirm ? 'Hide password' : 'Show password'}
                >
                  {showConfirm ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
            </div>

            <div className="form-group checkbox-group">
              <input
                id="terms"
                type="checkbox"
                checked={agreeToTerms}
                onChange={(e) => setAgreeToTerms(e.target.checked)}
                className="form-checkbox"
                disabled={isLoading}
              />
              <label htmlFor="terms" className="checkbox-label">
                I agree to the{' '}
                <Link href="/terms" className="auth-link">
                  Terms of Service
                </Link>
                {' '}and{' '}
                <Link href="/privacy" className="auth-link">
                  Privacy Policy
                </Link>
              </label>
            </div>

            <button
              type="submit"
              className="auth-button"
              disabled={isLoading}
            >
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Already have an account?{' '}
              <Link href="/auth/login" className="auth-link">
                Sign in instead
              </Link>
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push('/')}
            className="back-link"
          >
            ← Back to Home
          </button>
        </div>

        <div className="auth-sidebar">
          <div className="sidebar-content">
            <h2>Get Started</h2>
            <ul className="benefits-list">
              <li>✓ Discover your signature scent</li>
              <li>✓ AI-powered recommendations</li>
              <li>✓ Join 50K+ fragrance lovers</li>
              <li>✓ Save your favorites</li>
              <li>✓ 100% privacy guaranteed</li>
            </ul>
            <p className="sidebar-footer">
              <strong>Free account.</strong> Start exploring today.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
