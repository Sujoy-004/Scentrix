export interface Family {
  slug: string;
  name: string;
  tagline: string;
  description: string;
}

export const FAMILIES: Family[] = [
  { slug: 'amber', name: 'Amber', tagline: 'Resinous Warmth', description: 'Sweet, sensual, and warm. Amber fragrances create a cozy aura with vanilla, tonka bean, and musk notes.' },
  { slug: 'animalic', name: 'Animalic', tagline: 'Raw Sensuality', description: 'Primitive, raw, and hypnotic. Animalic scents evoke natural magnetism with musky, leathery, and earthy undertones.' },
  { slug: 'aquatic', name: 'Aquatic', tagline: 'Oceanic Mist', description: 'Light, airy, and refreshing. Aquatic fragrances evoke the ocean with fresh, ozonic, and saline notes.' },
  { slug: 'aromatic', name: 'Aromatic', tagline: 'Herbal Harmony', description: 'Fresh, herbal, and invigorating. Aromatic fragrances feature lavender, rosemary, and sage.' },
  { slug: 'citrus', name: 'Citrus', tagline: 'Zesty Vibrance', description: 'Bright, fresh, and energizing. Citrus fragrances open with zesty top notes of bergamot, lemon, and orange.' },
  { slug: 'earthy', name: 'Earthy', tagline: 'Foraged Roots', description: 'Deep, damp, and natural. Earthy scents capture the essence of soil, moss, and forest floors.' },
  { slug: 'floral', name: 'Floral', tagline: 'Delicate Petals', description: 'Delicate, romantic, and elegant. Floral fragrances celebrate the beauty of flowers like roses and jasmine.' },
  { slug: 'fresh', name: 'Fresh', tagline: 'Crisp Morning', description: 'Crisp, clean, and breezy. Fresh fragrances capture the lightness of mountain air and pure water.' },
  { slug: 'fruity', name: 'Fruity', tagline: 'Sun-Drenched', description: 'Juicy, playful, and vibrant. Fruity fragrances burst with apple, peach, and tropical berry notes.' },
  { slug: 'gourmand', name: 'Gourmand', tagline: 'Divine Sweets', description: 'Sweet, edible, and indulgent. Gourmand scents feature notes of chocolate, caramel, and vanilla.' },
  { slug: 'green', name: 'Green', tagline: 'Verdant Leaves', description: 'Lush, leafy, and natural. Green fragrances evoke crushed leaves and freshly cut grass.' },
  { slug: 'leather', name: 'Leather', tagline: 'Tanned Elegance', description: 'Sleek, smoky, and sophisticated. Leather scents capture the rich aroma of fine suede and cured hides.' },
  { slug: 'musky', name: 'Musky', tagline: 'Velvet Aura', description: 'Soft, powdery, and intimate. Musky fragrances create a second-skin feel with a clean, sensual depth.' },
  { slug: 'oriental', name: 'Oriental', tagline: 'Exotic Splendor', description: 'Exotic, opulent, and spicy. Oriental fragrances blend warm resins with precious woods and spices.' },
  { slug: 'powdery', name: 'Powdery', tagline: 'Silk Dust', description: 'Soft, vintage, and comforting. Powdery scents evoke fine cosmetics and clean linens.' },
  { slug: 'smoky', name: 'Smoky', tagline: 'Incense & Embers', description: 'Incense, ash, and charcoal. Smoky fragrances provide a mysterious, deep, and primitive allure.' },
  { slug: 'spicy', name: 'Spicy', tagline: 'Warm Sands', description: 'Vibrant, warm, and sharp. Spicy scents feature pepper, cardamom, cinnamon, and cloves.' },
  { slug: 'woody', name: 'Woody', tagline: 'Ancient Forests', description: 'Rich, warm, and grounding. Woody fragrances feature deep notes of sandalwood, cedar, and vetiver.' },
];

export const FAMILY_MAP: Record<string, Family> = Object.fromEntries(
  FAMILIES.map((f) => [f.slug, f])
);

export function getFamilyBySlug(slug: string): Family | undefined {
  return FAMILY_MAP[slug];
}