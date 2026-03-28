import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = Object.assign(
  axios.create({
    baseURL: BASE_URL,
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' },
  }),
  {
    getFragranceCatalog: async (limit: number, offset: number) => {
      try {
        const { data } = await axios.get(`${BASE_URL}/fragrances/catalog`, { params: { limit, offset } });
        return data;
      } catch {
        return { items: [] };
      }
    },
  }
);

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
}