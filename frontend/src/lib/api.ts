import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
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
        // 1. Synthesize Semantic Query against Neural Engine
        const { data: jobData } = await apiInstance.post('/fragrances/recommend/text', {
          query: filters.q,
          limit: limit
        });
        
        if (!jobData || !jobData.job_id) return { items: [], total: 0 };

        // 2. Asynchronous Neural Polling Loop (Max 30 seconds)
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
  submitRating: async (id: string, rating: number) => {
    const { data } = await apiInstance.post(`/fragrances/${id}/rate`, { rating });
    return data;
  },
  getGuestRecommendations: async (ratings: { fragrance_id: string; rating: number }[]) => {
    const { data } = await apiInstance.post('/recommendations/guest', { ratings });
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