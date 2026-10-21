import axios, { type AxiosRequestConfig } from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// A free-tier API scales to zero when idle, so the first request after a
// quiet period pays for the wake-up. 20s leaves room for that without the
// user staring at a spinner, and the retry below covers the gap.
const REQUEST_TIMEOUT = 20_000;

const apiInstance = axios.create({
  baseURL: BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
});

// Retry once when the instance is waking up or the edge dropped the request.
// 4xx is never retried - the request itself is wrong.
type RetriableConfig = AxiosRequestConfig & { __retried?: boolean };

const RETRYABLE_STATUS = new Set([502, 503, 504]);
apiInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const isNetworkError = !error?.response;
    const config = error?.config as RetriableConfig | undefined;
    const shouldRetry =
      (isNetworkError || (status && RETRYABLE_STATUS.has(status))) && !config?.__retried;

    if (!shouldRetry || !config) {
      throw error;
    }

    config.__retried = true;
    await new Promise((resolve) => setTimeout(resolve, 1500));
    return apiInstance.request(config);
  },
);

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

  getFragranceDetail: async (fragranceId: string) => {
    const { data } = await apiInstance.get(`/fragrances/${encodeURIComponent(fragranceId)}`);
    return data;
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

  guestFinalizeQuizSession: async (sessionId: string) => {
    const { data } = await apiInstance.post(`/fragrances/quiz/session/${sessionId}/guest-finalize`);
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
  year?: number | string;
  concentration?: string;
  gender_label?: string;
}