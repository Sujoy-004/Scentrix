/**
 * Collection Management Types
 * Scaffold for the "Collection Management" feature expansion.
 * Aligns with backend SavedFragrance schema in app/schemas/schemas.py
 */

export interface CollectionItem {
  id: number;
  fragrance_neo4j_id: string;
  name: string;
  brand: string;
  notes?: string;          // User's personal notes on this fragrance
  saved_at?: string;       // ISO date string
  match_score?: number;    // Score at time of saving, if available
}

export interface Collection {
  id: string;
  name: string;
  description?: string;
  items: CollectionItem[];
  created_at: string;
  updated_at?: string;
}

export interface CollectionCreatePayload {
  name: string;
  description?: string;
  fragrance_ids?: string[];
}

export interface CollectionUpdatePayload {
  name?: string;
  description?: string;
}
