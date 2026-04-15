import axios from 'axios';

const BASE_URL = typeof window === 'undefined' 
  ? process.env.INTERNAL_API_URL || 'http://backend:8000'
  : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

export const api = {
  get: apiInstance.get.bind(apiInstance),
  post: apiInstance.post.bind(apiInstance),
  put: apiInstance.put.bind(apiInstance),
  delete: apiInstance.delete.bind(apiInstance),
  patch: apiInstance.patch.bind(apiInstance),
  
  getFragranceCatalog: async (limit: number, offset: number, filters?: { q?: string; brand?: string; family?: string; sort?: string }) => {
    try {
      if (filters?.q) {
        const { data: jobData } = await apiInstance.post('/fragrances/recommend/text', {
          query: filters.q,
          limit: limit
        });
        
        if (!jobData || !jobData.job_id) return { items: [], total: 0 };

        for (let i = 0; i < 20; i++) {
          await new Promise(r => setTimeout(r, 1500));
          const { data: result } = await apiInstance.get(`/fragrances/recommend/${jobData.job_id}`);
          
          if (result.status === 'completed') {
             return { items: result.fragrances || [], total: (result.fragrances || []).length };
          }
          if (result.status === 'failed') break;
        }
        
        return { items: [], total: 0 };
      }
      
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

  getGuestRecommendations: async (ratings: { fragrance_id: string; rating: number; top_notes?: string[]; accords?: string[]; name?: string; brand?: string }[]) => {
    const { data } = await apiInstance.post('/recommendations/guest', { ratings });
    return data;
  },

  // Fixed: maps to the correct backend endpoint name (/personalized not /for-me)
  getPersonalizedRecommendations: async () => {
    const { data } = await apiInstance.get('/recommendations/personalized');
    return Array.isArray(data) ? data : [];
  },
  // Adaptive Quiz Protocol
  submitQuizResponse: async (sessionId: string, payload: { fragrance_id: string; rating_1_to_10: number; source: string }) => {
    const { data } = await apiInstance.post(`/quiz/session/${sessionId}/responses`, payload);
    return data;
  },

  evaluateQuizSession: async (sessionId: string, payload: { force: boolean }) => {
    const { data } = await apiInstance.post(`/quiz/session/${sessionId}/evaluate`, payload);
    return data;
  },

  getNextQuizQuestions: async (sessionId: string, count: number) => {
    const { data } = await apiInstance.get(`/quiz/session/${sessionId}/next-questions`, {
      params: { count }
    });
    return data;
  },

  finalizeQuizSession: async (sessionId: string) => {
    const { data } = await apiInstance.post(`/quiz/session/${sessionId}/finalize`);
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