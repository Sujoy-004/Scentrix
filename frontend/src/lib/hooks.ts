import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from './api';
import { useAppStore } from '@/stores/app-store';

export function useLogin() {
  const { quizResponses, setAuthToken } = useAppStore();
  return useMutation({
    mutationFn: async ({ email, password }: any) => {
      const { data } = await api.post('/auth/login', { email, password });
      
      // Store token so subsequent requests (like batch-rate) are authenticated
      if (data.access_token) {
        localStorage.setItem('auth_token', data.access_token);
        setAuthToken(data.access_token);
        
        // Sync local guest data to the fresh account
        if (quizResponses.length > 0) {
          try {
            await api.batchSubmitRatings(quizResponses.map(r => ({
              fragrance_id: r.fragrance_id,
              rating: r.rating
            })));
          } catch (e) {
            console.warn("Post-login sync failed:", e);
          }
        }
      }
      return data;
    },
  });
}

export function useRegister() {
  const { quizResponses, setAuthToken } = useAppStore();
  return useMutation({
    mutationFn: async ({ email, password, full_name }: { email: string; password: string; full_name?: string }) => {
      const { data } = await api.post('/auth/register', { email, password, full_name });
      
      // Store token so subsequent requests are authenticated
      if (data.access_token) {
        localStorage.setItem('auth_token', data.access_token);
        setAuthToken(data.access_token);

        // Sync local guest data to the fresh account
        if (quizResponses.length > 0) {
          try {
            await api.batchSubmitRatings(quizResponses.map(r => ({
              fragrance_id: r.fragrance_id,
              rating: r.rating
            })));
          } catch (e) {
            console.warn("Post-register sync failed:", e);
          }
        }
      }
      return data;
    },
  });
}


export function useRecommendations() {
  const { isAuthenticated, quizResponses } = useAppStore();

  return useQuery({
    queryKey: ['recommendations', isAuthenticated],
    queryFn: async () => {
      // Guests: do NOT fetch — the page will show the auth gate instead.
      if (!isAuthenticated) return null;

      // Authenticated: fetch from personalized endpoint.
      return api.getPersonalizedRecommendations();
    },
    enabled: isAuthenticated, // only run for logged-in users
    retry: (failureCount, error: any) => {
      if (error?.response?.status >= 400 && error?.response?.status < 500) return false;
      return failureCount < 2;
    },
  });
}


export function useUserProfile() {
  return useQuery({
    queryKey: ['user-profile'],
    queryFn: async () => {
      const { data } = await api.get('/user/profile');
      return data;
    },
  });
}

export function useUpdateUserPreferences() {
  return useMutation({
    mutationFn: async (prefs: any) => {
      const { data } = await api.post('/user/preferences', prefs);
      return data;
    },
  });
}

export function useWishlist() {
  return useQuery({
    queryKey: ['wishlist'],
    queryFn: async () => {
      const { data } = await api.get('/user/wishlist');
      return Array.isArray(data) ? data : [];
    },
  });
}

export function useRemoveFromWishlist() {
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/user/wishlist/${id}`);
      return data;
    },
  });
}

export function useSubmitRating() {
  return useMutation({
    mutationFn: async ({ fragranceId, rating }: { fragranceId: string; rating: number }) => {
      return api.submitRating(fragranceId, rating);
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
    mutationFn: async ({ sessionId, ...payload }: { sessionId: string; [key: string]: any }) => {
      const { data } = await api.post(`/quiz/session/${sessionId}/evaluate`, payload);
      return data;
    },
  });

  const extendSession = useMutation({
    mutationFn: async ({ sessionId, ...payload }: { sessionId: string; [key: string]: any }) => {
      const { data } = await api.post(`/quiz/session/${sessionId}/extend`, payload);
      return data;
    },
  });

  const submitResponse = useMutation({
    mutationFn: async ({ sessionId, ...payload }: { sessionId: string; [key: string]: any }) => {
      const { data } = await api.post(`/quiz/session/${sessionId}/response`, payload);
      return data;
    },
  });

  const fetchNextQuestions = useMutation({
    mutationFn: async ({ sessionId, ...payload }: { sessionId: string; [key: string]: any }) => {
      const { data } = await api.post(`/quiz/session/${sessionId}/next`, payload);
      return data;
    },
  });

  return { startSession, evaluateSession, extendSession, submitResponse, fetchNextQuestions };
}

export function useFragranceCatalog(limit: number, offset: number, filters?: { q?: string; brand?: string; family?: string }) {
  return useQuery({
    queryKey: ['fragrance-catalog', limit, offset, filters],
    queryFn: () => api.getFragranceCatalog(limit, offset, filters),
  });
}