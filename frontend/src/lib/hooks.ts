import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from './api';
import { useAppStore } from '@/stores/app-store';

export function useRecommendations() {
  const { quizResponses, quizConfidence } = useAppStore();

  const query = useQuery({
    queryKey: ['recommendations', quizResponses.length, !!quizConfidence],
    queryFn: async () => {
      const result = await api.getGuestRecommendations(
        quizResponses.map(r => ({
          fragrance_id: r.fragrance_id,
          rating: r.rating,
          top_notes: r.top_notes,
          accords: r.accords,
          name: r.name,
          brand: r.brand
        })),
        quizConfidence,
      );

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