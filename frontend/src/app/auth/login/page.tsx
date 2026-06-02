'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useLogin } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import { api } from '@/lib/api';
import posthog from 'posthog-js';
import '../auth.css';

type LoginSuccessPayload = {
  access_token?: string;
  user_id?: string;
};

type LoginErrorPayload = {
  response?: {
    data?: {
      detail?: unknown;
    };
    status?: number;
  };
  code?: string;
};

function getLoginErrorMessage(err: unknown): string {
  const parsed = err as LoginErrorPayload;
  const detail = parsed?.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === 'string' && first.trim()) {
      return first;
    }
    if (typeof first?.msg === 'string' && first.msg.trim()) {
      return first.msg;
    }
  }

  if (typeof detail === 'object' && detail !== null && 'msg' in detail) {
    const obj = detail as { msg?: string };
    if (typeof obj.msg === 'string' && obj.msg.trim()) {
      return obj.msg;
    }
  }

  const status = parsed?.response?.status;
  if (status === 401) {
    return 'Invalid email or password';
  }
  if (status === 403) {
    return 'User account is inactive';
  }
  if (parsed?.code === 'ERR_NETWORK') {
    return 'Cannot reach server. Please try again.';
  }

  return 'Login failed. Please try again.';
}

function getLoginErrorFromQuery(): string {
  if (typeof window === 'undefined') {
    return '';
  }

  const searchParams = new URLSearchParams(window.location.search);
  const supported = new Set(['error', 'message', 'next']);
  const keys = Array.from(searchParams.keys());
  const unknownKeys = keys.filter((key) => !supported.has(key));

  if (unknownKeys.length > 0) {
    return 'Invalid login link. Please sign in with your email and password.';
  }

  const urlError = searchParams.get('error') || searchParams.get('message');
  return urlError && urlError.trim() ? urlError : '';
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(() => getLoginErrorFromQuery());
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const loginMutation = useLogin();
  const { setAuthToken, setUserId, clearQuizResponses } = useAppStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!email || !password) {
      setError('Please fill in all fields');
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

    setIsLoading(true);

    loginMutation.mutate(
      { email, password },
      {
        onSuccess: async (data: LoginSuccessPayload) => {
          if (!data?.access_token) {
            setError('Login failed. Invalid server response.');
            return;
          }

          setAuthToken(data.access_token);
          if (data.user_id) {
            setUserId(data.user_id);
            // Identify user in PostHog
            posthog.identify(data.user_id, {
               email: email 
            });
            posthog.capture('user_login', { method: 'email' });
          }

          let syncWarning = false;
          const store = useAppStore.getState();
          if (store.quizResponses && store.quizResponses.length > 0) {
            const syncResults = await Promise.allSettled(
              store.quizResponses.map((response) =>
                api.submitRating(response.fragrance_id, response.rating)
              )
            );
            syncWarning = syncResults.some((result) => result.status === 'rejected');
            if (!syncWarning) {
              clearQuizResponses();
            }
          }

          router.push(syncWarning ? '/recommendations?sync=partial' : '/recommendations');
        },
        onError: (err: unknown) => {
          setError(getLoginErrorMessage(err));
        },
        onSettled: () => {
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
            <h1>Welcome Back</h1>
            <p>Sign in to continue your fragrance journey</p>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            {error && <div className="error-message">{error}</div>}

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
                  placeholder="••••••••"
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


            <button
              type="submit"
              className="auth-button"
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="auth-footer">
            <p>
              Don&apos;t have an account?{' '}
              <Link href="/auth/register" className="auth-link">
                Sign up here
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
            <h2>Why Sign In?</h2>
            <ul className="benefits-list">
              <li>Save your fragrance preferences</li>
              <li>Get personalized recommendations</li>
              <li>Build your fragrance collection</li>
              <li>Access your quiz results anytime</li>
              <li>Sync across all devices</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
