'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRegister } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import './auth.css';

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const registerMutation = useRegister();
  const { setAuthToken, setUserId } = useAppStore();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const validateForm = () => {
    if (!formData.email || !formData.password || !formData.confirmPassword || !formData.fullName) {
      setError('Please fill in all fields');
      return false;
    }

    if (!formData.email.includes('@')) {
      setError('Please enter a valid email address');
      return false;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return false;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }

    if (formData.fullName.length < 2) {
      setError('Please enter your full name');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (!validateForm()) {
      setIsLoading(false);
      return;
    }

    registerMutation.mutate(
      {
        email: formData.email,
        password: formData.password,
        full_name: formData.fullName,
      },
      {
        onSuccess: (data) => {
          setAuthToken(data.access_token);
          setUserId(data.user_id);
          router.push('/onboarding/quiz');
        },
        onError: (err: any) => {
          setError(
            err.response?.data?.detail ||
              'Registration failed. Please try again.'
          );
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
              <label htmlFor="fullName">Full Name</label>
              <input
                id="fullName"
                name="fullName"
                type="text"
                placeholder="John Doe"
                value={formData.fullName}
                onChange={handleChange}
                className="form-input"
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <input
                id="email"
                name="email"
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                className="form-input"
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                className="form-input"
                disabled={isLoading}
              />
              <p className="password-hint">Min. 8 characters</p>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={formData.confirmPassword}
                onChange={handleChange}
                className="form-input"
                disabled={isLoading}
              />
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
              <button
                type="button"
                onClick={() => router.push('/auth/login')}
                className="auth-link"
              >
                Sign in here
              </button>
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
