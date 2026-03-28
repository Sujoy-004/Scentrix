import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

export interface FragranceCatalogItem {
  id: string;
  brand: string;
  name: string;
  top_notes: string[];
  middle_notes: string[];
  base_notes: string[];
  family: string;
  description?: string;
  image_url?: string;
}