export interface Fragrance {
  id: string;
  brand: string;
  name: string;
  top_notes: string[];
  family: string;
}

const FRAGRANCES: Fragrance[] = [
  { id: '1', brand: 'Chanel', name: 'Bleu de Chanel', top_notes: ['Citrus', 'Mint', 'Pink Pepper'], family: 'Woody' },
  { id: '2', brand: 'Dior', name: 'Sauvage', top_notes: ['Bergamot', 'Pepper', 'Lavender'], family: 'Fresh' },
  { id: '3', brand: 'Tom Ford', name: 'Oud Wood', top_notes: ['Oud', 'Rosewood', 'Cardamom'], family: 'Oriental' },
  { id: '4', brand: 'Creed', name: 'Aventus', top_notes: ['Pineapple', 'Bergamot', 'Blackcurrant'], family: 'Chypre' },
  { id: '5', brand: 'YSL', name: 'Black Opium', top_notes: ['Coffee', 'Vanilla', 'White Flowers'], family: 'Oriental' },
  { id: '6', brand: 'Hermes', name: 'Terre dHermes', top_notes: ['Orange', 'Flint', 'Pepper'], family: 'Woody' },
];

export function getFeaturedFragrances(count: number): Fragrance[] {
  return FRAGRANCES.slice(0, count);
}
