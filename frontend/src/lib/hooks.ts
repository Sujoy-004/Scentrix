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
  const { isAuthenticated, quizResponses, quizConfidence } = useAppStore();

  const query = useQuery({
    queryKey: ['recommendations', isAuthenticated, quizResponses.length, !!quizConfidence],
    queryFn: async () => {
      let result: any;

      if (isAuthenticated) {
        result = await api.getPersonalizedRecommendations();
      } else if (quizConfidence) {
        result = await api.getGuestRecommendations(
          quizResponses.map(r => ({
            fragrance_id: r.fragrance_id,
            rating: r.rating,
          })),
          quizConfidence,
        );
      } else {
        result = await api.getGuestRecommendations(
          quizResponses.map(r => ({
            fragrance_id: r.fragrance_id,
            rating: r.rating,
            top_notes: r.top_notes,
            accords: r.accords,
            name: r.name,
            brand: r.brand
          })),
          null
        );
      }

      return {
        recommendations: result?.data ?? [],
        state: result?.state ?? null,
        stateLabel: result?.state_label ?? null,
      };
    },
    enabled: true,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 403) return false;
      return failureCount < 2;
    },
  });

  return {
    ...query,
    data: query.data?.recommendations ?? [],
    state: query.data?.state ?? null,
    stateLabel: query.data?.stateLabel ?? null,
  };
}


export function useUserProfile() {
  return useQuery({
    queryKey: ['user-profile'],
    queryFn: async () => {
      const { data } = await api.get('/users/profile');
      return data;
    },
  });
}

export function useUpdateUserPreferences() {
  return useMutation({
    mutationFn: async (prefs: any) => {
      const { data } = await api.post('/users/preferences', prefs);
      return data;
    },
  });
}

export function useWishlist() {
  return useQuery({
    queryKey: ['wishlist'],
    queryFn: async () => {
      const { data } = await api.get('/users/saved');
      return Array.isArray(data) ? data : [];
    },
  });
}

export function useRemoveFromWishlist() {
  return useMutation({
    mutationFn: async (id: number | string) => {
      const { data } = await api.delete(`/users/saved/${id}`);
      return data;
    },
  });
}

export function useUpdateSavedNotes() {
  return useMutation({
    mutationFn: async ({ id, notes }: { id: number; notes: string }) => {
      const { data } = await api.patch(`/users/saved/${id}/notes`, { notes });
      return data;
    },
  });
}

export function useAddToCollection() {
  return useMutation({
    mutationFn: async ({ fragranceId, notes }: { fragranceId: string; notes?: string }) => {
      const { data } = await api.post('/users/saved', {
        fragrance_neo4j_id: fragranceId,
        notes
      });
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
    mutationFn: (payload: { seed_count: number; candidate_pool_size: number; filters: any }) =>
      api.startQuizSession(payload),
  });

  const evaluateSession = useMutation({
    mutationFn: ({ sessionId, ...payload }: { sessionId: string;[key: string]: any }) =>
      api.evaluateQuizSession(sessionId, payload as any),
  });

  const submitResponse = useMutation({
    mutationFn: ({ sessionId, ...payload }: { sessionId: string;[key: string]: any }) =>
      api.submitQuizResponse(sessionId, payload as any),
  });

  const fetchNextQuestions = useMutation({
    mutationFn: ({ sessionId, count }: { sessionId: string; count: number }) =>
      api.getNextQuizQuestions(sessionId, count),
  });

  return { startSession, evaluateSession, submitResponse, fetchNextQuestions };
}

export function useFragranceCatalog(limit: number, offset: number, filters?: { q?: string; brand?: string; family?: string }) {
  return useQuery({
    queryKey: ['fragrance-catalog', limit, offset, filters],
    queryFn: () => api.getFragranceCatalog(limit, offset, filters),
  });
}

export function useQuizSummary() {
  return useQuery({
    queryKey: ['quiz-summary'],
    queryFn: async () => {
      const res = await api.getQuizSummary();
      return res?.data ?? null;
    },
  });
}