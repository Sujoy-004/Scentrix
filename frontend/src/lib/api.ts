import axios, { type AxiosRequestConfig } from 'axios';

import { useToastStore } from '@/stores/toast-store';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// The API runs on a free-tier host that scales to zero when idle. A warm
// instance answers in ~50 ms; a cold one needs up to a minute to boot, and
// the proxy holds the request open while that happens. So: try fast, and on
// a timeout or a gateway error assume the instance is waking and try once
// more with a generous timeout.
const WARM_TIMEOUT = 10_000;
const COLD_START_TIMEOUT = 80_000;

const apiInstance = axios.create({
  baseURL: BASE_URL,
  timeout: WARM_TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
});

// Retry once when the instance is waking up or the edge dropped the request.
// 4xx is never retried - the request itself is wrong.
type RetriableConfig = AxiosRequestConfig & { __retried?: boolean };

const RETRYABLE_STATUS = new Set([502, 503, 504]);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

apiInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const code = error?.code;
    const isTimeout = code === 'ECONNABORTED' || code === 'ETIMEDOUT';
    const isNetworkError = !error?.response;

    const config = error?.config as RetriableConfig | undefined;
    if (!config || config.__retried) {
      throw error;
    }

    const mightBeWaking =
      isTimeout || isNetworkError || (status && RETRYABLE_STATUS.has(status));
    if (!mightBeWaking) {
      throw error;
    }

    config.__retried = true;
    config.timeout = COLD_START_TIMEOUT;

    useToastStore.getState().addToast({
      message: 'Waking up the server - this can take up to a minute.',
      type: 'info',
      duration: 30_000,
    });

    await sleep(1500);
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