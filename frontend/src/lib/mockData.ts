export interface MockFragrance {
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

export const mockFragrances: MockFragrance[] = [
  {
    id: '1',
    brand: 'Chanel',
    name: 'Bleu de Chanel',
    family: 'woody',
    top_notes: ['Grapefruit', 'Lemon', 'Mint'],
    accords: ['Citrus', 'Woody', 'Fresh Spicy'],
  },
  {
    id: '2',
    brand: 'Dior',
    name: 'Sauvage',
    family: 'aromatic',
    top_notes: ['Bergamot', 'Pepper'],
    accords: ['Fresh Spicy', 'Amber', 'Citrus'],
  },
  {
    id: '3',
    brand: 'Creed',
    name: 'Aventus',
    family: 'chypre',
    top_notes: ['Pineapple', 'Bergamot', 'Black Currant'],
    accords: ['Fruity', 'Sweet', 'Leather'],
  },
  {
    id: '4',
    brand: 'Tom Ford',
    name: 'Tobacco Vanille',
    family: 'amber',
    top_notes: ['Tobacco Leaf', 'Spices'],
    accords: ['Vanilla', 'Sweet', 'Tobacco'],
  },
];

export function getFragrancesByFamily(family: string): MockFragrance[] {
  return mockFragrances.filter(f => f.family?.toLowerCase() === family.toLowerCase());
}

export function getFragranceById(id: string): MockFragrance | undefined {
  return mockFragrances.find(f => f.id === id);
}
