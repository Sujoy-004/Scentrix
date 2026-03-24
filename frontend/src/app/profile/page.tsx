'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUserProfile, useUpdateUserPreferences } from '@/lib/hooks';
import { useAppStore } from '@/stores/app-store';
import './profile.css';

export default function ProfilePage() {
  const router = useRouter();
  const { isAuthenticated } = useAppStore();
  const { data: profile, isLoading, error } = useUserProfile();
  const updatePrefMutation = useUpdateUserPreferences();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="profile-loading">
        <div className="loading-spinner">
          <p>Loading profile...</p>
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="profile-error">
        <h2>Unable to load profile</h2>
        <p>Please try again later.</p>
        <button
          className="error-button"
          onClick={() => router.push('/')}
        >
          Back to Home
        </button>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-container">
        {/* Header */}
        <div className="profile-header">
          <div>
            <h1>Your Profile</h1>
            <p>Manage your account and preferences</p>
          </div>
          <button
            className="back-to-home"
            onClick={() => router.push('/')}
          >
            ← Back to Home
          </button>
        </div>

        <div className="profile-grid">
          {/* Account Section */}
          <div className="profile-section">
            <h2 className="section-title">Account Information</h2>
            <div className="info-card">
              <div className="info-group">
                <label>Name</label>
                <p className="info-value">{profile?.full_name || 'N/A'}</p>
              </div>
              <div className="info-group">
                <label>Email</label>
                <p className="info-value">{profile?.email || 'N/A'}</p>
              </div>
              <div className="info-group">
                <label>Member Since</label>
                <p className="info-value">
                  {profile?.created_at
                    ? new Date(profile.created_at).toLocaleDateString()
                    : 'N/A'}
                </p>
              </div>
              <button
                className="edit-button"
                onClick={() => router.push('/profile/edit')}
              >
                Edit Account
              </button>
            </div>
          </div>

          {/* Preferences Section */}
          <div className="profile-section">
            <h2 className="section-title">Fragrance Preferences</h2>
            <div className="prefs-card">
              <div className="pref-item">
                <span className="pref-label">Favorite Families</span>
                <p className="pref-value">
                  {profile?.preferences?.favorite_families?.join(', ') ||
                    'Not set'}
                </p>
              </div>
              <div className="pref-item">
                <span className="pref-label">Preferred Intensity</span>
                <p className="pref-value">
                  {profile?.preferences?.preferred_intensity || 'Moderate'}
                </p>
              </div>
              <div className="pref-item">
                <span className="pref-label">Budget Range</span>
                <p className="pref-value">
                  {profile?.preferences?.budget_range || 'Any'}
                </p>
              </div>
              <button
                className="edit-button"
                onClick={() => router.push('/profile/preferences')}
              >
                Edit Preferences
              </button>
            </div>
          </div>

          {/* Stats Section */}
          <div className="profile-section stats-section">
            <h2 className="section-title">Your Stats</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-number">
                  {profile?.quiz_count || 0}
                </span>
                <span className="stat-label">Quizzes Taken</span>
              </div>
              <div className="stat-card">
                <span className="stat-number">
                  {profile?.wishlist_count || 0}
                </span>
                <span className="stat-label">Saved Fragrances</span>
              </div>
              <div className="stat-card">
                <span className="stat-number">
                  {profile?.recommendation_count || 0}
                </span>
                <span className="stat-label">Recommendations</span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="quick-actions">
          <button
            className="action-button"
            onClick={() => router.push('/onboarding/quiz')}
          >
            Retake Quiz
          </button>
          <button
            className="action-button"
            onClick={() => router.push('/recommendations')}
          >
            View Recommendations
          </button>
          <button
            className="action-button"
            onClick={() => router.push('/profile/wishlist')}
          >
            My Wishlist
          </button>
        </div>

        {/* Account Actions */}
        <div className="account-actions">
          <h3>Account Actions</h3>
          <button
            className="danger-button"
            onClick={() => {
              if (confirm('Are you sure you want to delete your account? This cannot be undone.')) {
                alert('Account deletion requested. Please contact support.');
              }
            }}
          >
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
