/**
 * Scentrix "Quiet Luxury" Family Mapping Utility
 *
 * Maps raw backend accords/notes to the 19 premium olfactive family assets.
 * As per user request, failing to map will return a "failed : [reason]" string
 * instead of a default image.
 */

// Silent Luxury Palette Integration
export const SCENT_PALETTE: Record<string, string[]> = {
  oriental: ['#5A2A1B', '#C8A15A', '#1B0F12'],
  green: ['#0F3D2E', '#8FAE8B', '#D6E3D2'],
  woody: ['#3B2C24', '#8B6B4A', '#E6D8C8'],
  citrus: ['#B8860B', '#FFE08A', '#6B3A1F'],
  floral: ['#8B1A4A', '#E91E8C', '#4A3728'],
};

export const CANONICAL_FAMILIES = [
  'amber', 'animalic', 'aquatic', 'aromatic', 'citrus', 'earthy',
  'floral', 'fresh', 'fruity', 'gourmand', 'green', 'leather',
  'musky', 'oriental', 'powdery', 'smoky', 'spicy', 'woody', 'all'
];

const ACCORD_MAP: Record<string, string> = {
  // Wood
  'woody': 'woody',
  'sandalwood': 'woody',
  'cedar': 'woody',
  'vetiver': 'woody',
  'agarwood': 'woody',
  'oud': 'woody',
  
  // Floral
  'floral': 'floral',
  'rose': 'floral',
  'jasmine': 'floral',
  'white floral': 'floral',
  'violet': 'floral',
  'iris': 'floral',
  
  // Fresh/Citrus
  'citrus': 'citrus',
  'bergamot': 'citrus',
  'lemon': 'citrus',
  'orange': 'citrus',
  'fresh': 'fresh',
  'aquatic': 'aquatic',
  'marine': 'aquatic',
  'ozonic': 'aquatic',
  
  // Gourmand/Oriental
  'gourmand': 'gourmand',
  'vanilla': 'gourmand',
  'sweet': 'gourmand',
  'caramel': 'gourmand',
  'chocolate': 'gourmand',
  'oriental': 'oriental',
  'amber': 'amber',
  
  // Spice/Smoke
  'spicy': 'spicy',
  'warm spicy': 'spicy',
  'fresh spicy': 'spicy',
  'smoky': 'smoky',
  'incense': 'smoky',
  'tobacco': 'smoky',
  
  // Other
  'leather': 'leather',
  'animalic': 'animalic',
  'musky': 'musky',
  'musk': 'musky',
  'powdery': 'powdery',
  'green': 'green',
  'herbal': 'aromatic',
  'aromatic': 'aromatic',
  'earthy': 'earthy',
  'fruity': 'fruity',
};

export type AssetResult = {
  src: string | null;
  error: string | null;
};

/**
 * Translates a raw backend accord into a canonical asset path.
 * 
 * @param rawAccord The string from the backend (e.g. "Vanilla")
 * @returns {AssetResult} The asset path or an error description.
 */
export function getFamilyAsset(rawAccord: string | undefined | null): AssetResult {
  if (!rawAccord) {
    return { src: null, error: 'failed : missing accord' };
  }

  const normalized = rawAccord.toLowerCase().trim();
  
  // 1. Direct match with canonical list
  if (CANONICAL_FAMILIES.includes(normalized)) {
    return { src: `/assets/family/${normalized}.png`, error: null };
  }

  // 2. Map through dictionary
  const mapped = ACCORD_MAP[normalized];
  if (mapped) {
    return { src: `/assets/family/${mapped}.png`, error: null };
  }

  // 3. Fallback: Search for partial bits (e.g. "Woody Spicy")
  for (const [key, value] of Object.entries(ACCORD_MAP)) {
    if (normalized.includes(key)) {
      return { src: `/assets/family/${value}.png`, error: null };
    }
  }

  return { src: null, error: `failed : unknown family [${rawAccord}]` };
}
