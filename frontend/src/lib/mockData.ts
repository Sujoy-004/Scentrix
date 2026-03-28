export interface Fragrance {
  id: string;
  brand: string;
  name: string;
  top_notes: string[];
  middle_notes: string[];
  base_notes: string[];
  family: string;
  description?: string;
}

const FRAGRANCES: Fragrance[] = [
  { id: '1', brand: 'Chanel', name: 'Bleu de Chanel', top_notes: ['Citrus', 'Mint', 'Pink Pepper'], middle_notes: ['Ginger', 'Nutmeg'], base_notes: ['Sandalwood', 'Cedar'], family: 'Woody' },
  { id: '2', brand: 'Dior', name: 'Sauvage', top_notes: ['Bergamot', 'Pepper', 'Lavender'], middle_notes: ['Sichuan Pepper', 'Vetiver'], base_notes: ['Ambroxan', 'Cedar'], family: 'Fresh' },
  { id: '3', brand: 'Tom Ford', name: 'Oud Wood', top_notes: ['Oud', 'Rosewood', 'Cardamom'], middle_notes: ['Sandalwood', 'Vetiver'], base_notes: ['Amber', 'Musk'], family: 'Oriental' },
  { id: '4', brand: 'Creed', name: 'Aventus', top_notes: ['Pineapple', 'Bergamot', 'Blackcurrant'], middle_notes: ['Rose', 'Birch'], base_notes: ['Musk', 'Oak Moss'], family: 'Chypre' },
  { id: '5', brand: 'YSL', name: 'Black Opium', top_notes: ['Coffee', 'Vanilla', 'White Flowers'], middle_notes: ['Jasmine', 'Bitter Almond'], base_notes: ['Patchouli', 'Cedarwood'], family: 'Oriental' },
  { id: '6', brand: 'Hermes', name: 'Terre dHermes', top_notes: ['Orange', 'Flint', 'Pepper'], middle_notes: ['Pelargonium', 'Vetiver'], base_notes: ['Benzoin', 'Cedar'], family: 'Woody' },
];

export function getFeaturedFragrances(count: number): Fragrance[] {
  return FRAGRANCES.slice(0, count);
}

export function getAllFragrances(): Fragrance[] {
  return FRAGRANCES;
}

export function getFragrancesByFamily(family: string): Fragrance[] {
  return FRAGRANCES.filter(f => f.family === family);
}

export function getFragranceFamilies(): string[] {
  return [...new Set(FRAGRANCES.map(f => f.family))];
}

export function getQuizFragrances(count: number): Fragrance[] {
  return FRAGRANCES.slice(0, count);
}