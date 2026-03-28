import { useMutation } from '@tanstack/react-query';
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
  const fetchRecs = async () => {
    setLoading(true);
    try { const r = await api.get('/recommendations'); setData(r.data); }
    catch { setData([]); }
    finally { setLoading(false); }
  };
  return { data, loading, fetch: fetchRecs };
}

export function useUserProfile() {
  const [profile, setProfile] = useState<any>(null);
  return { profile, setProfile };
}

export function useUpdateUserPreferences() {
  const update = async (prefs: any) => {
    try { await api.post('/user/preferences', prefs); } catch { }
  };
  return { update };
}

export function useWishlist() {
  const [wishlist, setWishlist] = useState<any[]>([]);
  return { wishlist, setWishlist };
}

export function useRemoveFromWishlist() {
  const remove = async (id: string) => {
    try { await api.delete(`/user/wishlist/${id}`); } catch { }
  };
  return { remove };
}

export function useSubmitRating() {
  return useMutation({
    mutationFn: async ({ fragranceId, rating }: { fragranceId: string; rating: number }) => {
      const { data } = await api.post(`/fragrances/${fragranceId}/rate`, { rating });
      return data;
    },
  });
}

export function useAdaptiveQuizSession() {
  const startSession = useMutation({
    mutationFn: async (payload: { seed_count: number; candidate_pool_size: number; filters: any }) => {
      const { data } = await api.post('/quiz/session/start', payload);
      return data;
    },
  });

  const evaluateSession = useMutation({
    mutationFn: async ({ sessionId, payload }: { sessionId: string; payload: any }) => {
      const { data } = await api.post(`/quiz/session/${sessionId}/evaluate`, payload);
      return data;
    },
  });

  const extendSession = useMutation({
    mutationFn: async ({ sessionId, payload }: { sessionId: string; payload: any }) => {
      const { data } = await api.post(`/quiz/session/${sessionId}/extend`, payload);
      return data;
    },
  });

  const submitResponse = useMutation({
    mutationFn: async ({ sessionId, payload }: { sessionId: string; payload: any }) => {
      const { data } = await api.post(`/quiz/session/${sessionId}/response`, payload);
      return data;
    },
  });

  const fetchNextQuestions = useMutation({
    mutationFn: async ({ sessionId, payload }: { sessionId: string; payload: any }) => {
      const { data } = await api.post(`/quiz/session/${sessionId}/next`, payload);
      return data;
    },
  });

  return { startSession, evaluateSession, extendSession, submitResponse, fetchNextQuestions };
}