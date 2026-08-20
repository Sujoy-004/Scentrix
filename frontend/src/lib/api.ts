import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

if (!BASE_URL) {
  throw new Error("NEXT_PUBLIC_API_URL is not defined");
}

const apiInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 60000, // 60s for deep neural synthesis
  headers: { 'Content-Type': 'application/json' },
});

// Auto-inject JWT token for authenticated requests
apiInstance.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const VALID_IDS = [
  "frag_success",
  "frag_chic-blossom",
  "frag_sweet-sin",
  "frag_tutti-twilly-d-hermes",
  "frag_celebre-ice"
];

export const api = {
  get: apiInstance.get.bind(apiInstance),
  post: apiInstance.post.bind(apiInstance),
  put: apiInstance.put.bind(apiInstance),
  delete: apiInstance.delete.bind(apiInstance),
  patch: apiInstance.patch.bind(apiInstance),
  
  getFragranceCatalog: async (limit: number, offset: number, filters?: { q?: string; brand?: string; family?: string; sort?: string }) => {
    try {
      const { data } = await apiInstance.get('/fragrances/catalog', { 
        params: { limit, offset, ...filters } 
      });
      return data;
    } catch (e) {
      console.error("Neural Search Exception:", e);
      return { items: [], total: 0 };
    }
  },

  // Fixed: posts to the new dedicated /recommendations/rate endpoint
  submitRating: async (fragranceId: string, rating: number, meta?: { top_notes?: string[]; accords?: string[]; name?: string; brand?: string }) => {
    try {
      const { data } = await apiInstance.post('/recommendations/rate', {
        fragrance_id: fragranceId,
        rating,
        ...meta,
      });
      return data;
    } catch (e) {
      // Non-blocking: guest flow must never crash due to a rating sync failure
      console.warn('Rating sync failed (non-blocking):', e);
      return null;
    }
  },
  
  batchSubmitRatings: async (ratings: { fragrance_id: string; rating: number }[]) => {
    try {
      const { data } = await apiInstance.post('/recommendations/batch-rate', { ratings });
      return data;
    } catch (e) {
      console.error('Batch sync failed:', e);
      throw e;
    }
  },

  getGuestRecommendations: async (ratings: { 
    fragrance_id: string; 
    rating: number; 
    top_notes?: string[]; 
    accords?: string[]; 
    description?: string;
    name?: string; 
    brand?: string 
  }[], quiz_confidence?: Record<string, number> | null) => {
    const { data } = await apiInstance.post('/recommendations/guest', { 
      ratings, 
      ...(quiz_confidence ? { quiz_confidence } : {}) 
    });
    return data;
  },

  getPersonalizedRecommendations: async () => {
    const { data } = await apiInstance.get('/recommendations/personalized');
    return data;
  },
  // Adaptive Quiz Protocol
  startQuizSession: async (payload: { seed_count: number; candidate_pool_size: number; filters: any }) => {
    const { data } = await apiInstance.post('/fragrances/quiz/session/start', payload);
    return data;
  },

  submitQuizResponse: async (sessionId: string, payload: { fragrance_id: string; rating_1_to_10: number; source: string }) => {
    const { data } = await apiInstance.post(`/fragrances/quiz/session/${sessionId}/answer`, payload);
    return data;
  },

  evaluateQuizSession: async (sessionId: string, payload: { force: boolean }) => {
    const { data } = await apiInstance.post(`/fragrances/quiz/session/${sessionId}/evaluate`, payload);
    return data;
  },

  getNextQuizQuestions: async (sessionId: string, count: number) => {
    const { data } = await apiInstance.get(`/fragrances/quiz/session/${sessionId}/next-questions`, {
      params: { count }
    });
    return data;
  },

  finalizeQuizSession: async (sessionId: string) => {
    const { data } = await apiInstance.post(`/fragrances/quiz/session/${sessionId}/finalize`);
    return data;
  },

  guestFinalizeQuizSession: async (sessionId: string) => {
    const { data } = await apiInstance.post(`/fragrances/quiz/session/${sessionId}/guest-finalize`);
    return data;
  },

  getQuizSummary: async () => {
    const { data } = await apiInstance.get('/recommendations/quiz-summary');
    return data;
  },
};


export interface FragranceCatalogItem {
  id: string;
  brand: string;
  name: string;
  top_notes: string[];
  middle_notes?: string[];
  base_notes?: string[];
  accords?: string[];
  family?: string;
  description?: string;
  image_url?: string;
  rating?: number;
  popularity_score?: number;
  match_score?: number;
}