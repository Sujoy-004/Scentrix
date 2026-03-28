import { useState } from 'react';
import { api } from './api';

export function useLogin() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const login = async (email: string, password: string) => {
    setLoading(true);
    try { await api.post('/auth/login', { email, password }); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };
  return { login, loading, error };
}

export function useRegister() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const register = async (email: string, password: string) => {
    setLoading(true);
    try { await api.post('/auth/register', { email, password }); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };
  return { register, loading, error };
}

export function useRecommendations() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const fetch = async () => {
    setLoading(true);
    try { const r = await api.get('/recommendations'); setData(r.data); }
    catch { setData([]); }
    finally { setLoading(false); }
  };
  return { data, loading, fetch };
}

export function useUserProfile() {
  const [profile, setProfile] = useState<any>(null);
  return { profile, setProfile };
}

export function useUpdateUserPreferences() {
  const update = async (prefs: any) => {
    try { await api.post('/user/preferences', prefs); }
    catch { }
  };
  return { update };
}

export function useWishlist() {
  const [wishlist, setWishlist] = useState<any[]>([]);
  return { wishlist, setWishlist };
}

export function useRemoveFromWishlist() {
  const remove = async (id: string) => {
    try { await api.delete(`/user/wishlist/${id}`); }
    catch { }
  };
  return { remove };
}

export function useAdaptiveQuizSession() {
  const [session, setSession] = useState<any>(null);
  return { session, setSession };
}

export function useSubmitRating() {
  const submit = async (id: string, rating: number) => {
    try { await api.post(`/fragrances/${id}/rate`, { rating }); }
    catch { }
  };
  return { submit };
}