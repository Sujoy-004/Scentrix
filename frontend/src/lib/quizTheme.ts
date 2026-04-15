export interface FragrancePalette {
  soft: string;
  softSecondary: string;
  border: string;
  glow: string;
  accent: string;
  pageFrom: string;
  pageTo: string;
  beam: string;
  ink: string;
}

export function getFragrancePalette(item: any): FragrancePalette {
  let family = typeof item === 'string' ? item : (item?.family || 'Default');
  
  // High-Fidelity Heuristic: Deep Scan Accords & Notes for 'Vibe'
  const searchSpace = [
    ...(item?.accords || []),
    ...(item?.top_notes || []),
    item?.name || ''
  ].map(s => String(s).toLowerCase());

  if (searchSpace.some(s => s.includes('smoky') || s.includes('incense') || s.includes('smoke'))) family = 'Smoky';
  else if (searchSpace.some(s => s.includes('leather') || s.includes('suede'))) family = 'Leather';
  else if (searchSpace.some(s => s.includes('fresh') || s.includes('aquatic') || s.includes('water') || s.includes('marine'))) family = 'Fresh';
  else if (searchSpace.some(s => s.includes('citrus') || s.includes('lemon') || s.includes('zest') || s.includes('lime'))) family = 'Citrus';
  else if (searchSpace.some(s => s.includes('floral') || s.includes('rose') || s.includes('bloom') || s.includes('jasmine') || s.includes('iris'))) family = 'Floral';
  else if (searchSpace.some(s => s.includes('wood') || s.includes('oud') || s.includes('cedar') || s.includes('sandalwood'))) family = 'Woody';
  else if (searchSpace.some(s => s.includes('spicy') || s.includes('pepper') || s.includes('cardamom') || s.includes('cinnamon'))) family = 'Spicy';
  else if (searchSpace.some(s => s.includes('green') || s.includes('grass') || s.includes('leaf') || s.includes('herbal'))) family = 'Green';
  else if (searchSpace.some(s => s.includes('aromatic') || s.includes('lavender') || s.includes('sage') || s.includes('mint'))) family = 'Aromatic';
  else if (searchSpace.some(s => s.includes('amber') || s.includes('warm') || s.includes('vanilla') || s.includes('tonka'))) family = 'Amber';

  const palettes: Record<string, FragrancePalette> = {
    Woody: {
      soft: 'rgba(139, 94, 60, 0.08)',
      softSecondary: 'rgba(139, 94, 60, 0.15)',
      border: 'rgba(139, 94, 60, 0.3)',
      glow: 'rgba(139, 94, 60, 0.25)',
      accent: '#f4bb92',
      pageFrom: '#0a0908',
      pageTo: '#050404',
      beam: 'hsla(20, 20%, 60%, 0.1)',
      ink: '#f4bb92'
    },
    Fresh: {
      soft: 'rgba(127, 205, 255, 0.08)',
      softSecondary: 'rgba(127, 205, 255, 0.15)',
      border: 'rgba(127, 205, 255, 0.3)',
      glow: 'rgba(127, 205, 255, 0.25)',
      accent: '#7fcdff',
      pageFrom: '#080a0c',
      pageTo: '#040506',
      beam: 'hsla(200, 40%, 80%, 0.12)',
      ink: '#7fcdff'
    },
    Oriental: {
      soft: 'rgba(224, 128, 192, 0.08)',
      softSecondary: 'rgba(224, 128, 192, 0.15)',
      border: 'rgba(224, 128, 192, 0.3)',
      glow: 'rgba(224, 128, 192, 0.25)',
      accent: '#e080c0',
      pageFrom: '#0c080a',
      pageTo: '#060405',
      beam: 'hsla(320, 20%, 70%, 0.1)',
      ink: '#e080c0'
    },
    Chypre: {
      soft: 'rgba(118, 197, 118, 0.08)',
      softSecondary: 'rgba(118, 197, 118, 0.15)',
      border: 'rgba(118, 197, 118, 0.3)',
      glow: 'rgba(118, 197, 118, 0.25)',
      accent: '#76c576',
      pageFrom: '#080c08',
      pageTo: '#040604',
      beam: 'hsla(120, 20%, 70%, 0.1)',
      ink: '#76c576'
    },
    Floral: {
      soft: 'rgba(228, 130, 149, 0.08)',
      softSecondary: 'rgba(228, 130, 149, 0.15)',
      border: 'rgba(228, 130, 149, 0.3)',
      glow: 'rgba(228, 130, 149, 0.25)',
      accent: '#e48295',
      pageFrom: '#0c0808',
      pageTo: '#060404',
      beam: 'hsla(345, 30%, 75%, 0.1)',
      ink: '#e48295'
    },
    Amber: {
      soft: 'rgba(244, 187, 146, 0.08)',
      softSecondary: 'rgba(244, 187, 146, 0.15)',
      border: 'rgba(244, 187, 146, 0.3)',
      glow: 'rgba(244, 187, 146, 0.25)',
      accent: '#f4bb92',
      pageFrom: '#0c0b0a',
      pageTo: '#060505',
      beam: 'hsla(35, 30%, 70%, 0.12)',
      ink: '#f4bb92'
    },
    Animalic: {
      soft: 'rgba(139, 115, 85, 0.08)',
      softSecondary: 'rgba(139, 115, 85, 0.15)',
      border: 'rgba(139, 115, 85, 0.3)',
      glow: 'rgba(139, 115, 85, 0.25)',
      accent: '#8b7355',
      pageFrom: '#0a0908',
      pageTo: '#050404',
      beam: 'hsla(30, 15%, 65%, 0.1)',
      ink: '#8b7355'
    },
    Aquatic: {
      soft: 'rgba(127, 205, 255, 0.08)',
      softSecondary: 'rgba(127, 205, 255, 0.15)',
      border: 'rgba(127, 205, 255, 0.3)',
      glow: 'rgba(127, 205, 255, 0.25)',
      accent: '#7fcdff',
      pageFrom: '#080a0c',
      pageTo: '#040506',
      beam: 'hsla(200, 40%, 80%, 0.12)',
      ink: '#7fcdff'
    },
    Aromatic: {
      soft: 'rgba(100, 190, 185, 0.08)',
      softSecondary: 'rgba(100, 190, 185, 0.15)',
      border: 'rgba(100, 190, 185, 0.3)',
      glow: 'rgba(100, 190, 185, 0.25)',
      accent: '#64beb9',
      pageFrom: '#080c0b',
      pageTo: '#040605',
      beam: 'hsla(170, 25%, 75%, 0.12)',
      ink: '#64beb9'
    },
    Citrus: {
      soft: 'rgba(228, 194, 133, 0.08)',
      softSecondary: 'rgba(228, 194, 133, 0.15)',
      border: 'rgba(228, 194, 133, 0.3)',
      glow: 'rgba(228, 194, 133, 0.25)',
      accent: '#e4c285',
      pageFrom: '#0c0c08',
      pageTo: '#060604',
      beam: 'hsla(45, 30%, 75%, 0.12)',
      ink: '#e4c285'
    },
    Earthy: {
      soft: 'rgba(111, 78, 55, 0.08)',
      softSecondary: 'rgba(111, 78, 55, 0.15)',
      border: 'rgba(111, 78, 55, 0.3)',
      glow: 'rgba(111, 78, 55, 0.25)',
      accent: '#6f4e37',
      pageFrom: '#0a0908',
      pageTo: '#050404',
      beam: 'hsla(25, 15%, 65%, 0.1)',
      ink: '#6f4e37'
    },
    Gourmand: {
      soft: 'rgba(210, 105, 30, 0.08)',
      softSecondary: 'rgba(210, 105, 30, 0.15)',
      border: 'rgba(210, 105, 30, 0.3)',
      glow: 'rgba(210, 105, 30, 0.25)',
      accent: '#d2691e',
      pageFrom: '#0c0a08',
      pageTo: '#060504',
      beam: 'hsla(25, 25%, 70%, 0.1)',
      ink: '#d2691e'
    },
    Green: {
      soft: 'rgba(118, 197, 118, 0.08)',
      softSecondary: 'rgba(118, 197, 118, 0.15)',
      border: 'rgba(118, 197, 118, 0.3)',
      glow: 'rgba(118, 197, 118, 0.25)',
      accent: '#76c576',
      pageFrom: '#080c08',
      pageTo: '#040604',
      beam: 'hsla(120, 20%, 70%, 0.1)',
      ink: '#76c576'
    },
    Leather: {
      soft: 'rgba(139, 94, 60, 0.08)',
      softSecondary: 'rgba(139, 94, 60, 0.15)',
      border: 'rgba(139, 94, 60, 0.3)',
      glow: 'rgba(139, 94, 60, 0.25)',
      accent: '#f4bb92',
      pageFrom: '#0a0908',
      pageTo: '#050404',
      beam: 'hsla(15, 20%, 65%, 0.1)',
      ink: '#f4bb92'
    },
    Musky: {
      soft: 'rgba(180, 172, 155, 0.08)',
      softSecondary: 'rgba(180, 172, 155, 0.15)',
      border: 'rgba(180, 172, 155, 0.3)',
      glow: 'rgba(180, 172, 155, 0.25)',
      accent: '#b4ac9b',
      pageFrom: '#0c0c0c',
      pageTo: '#060606',
      beam: 'hsla(45, 10%, 80%, 0.1)',
      ink: '#b4ac9b'
    },
    Powdery: {
      soft: 'rgba(219, 112, 147, 0.08)',
      softSecondary: 'rgba(219, 112, 147, 0.15)',
      border: 'rgba(219, 112, 147, 0.3)',
      glow: 'rgba(219, 112, 147, 0.25)',
      accent: '#db7093',
      pageFrom: '#0c080a',
      pageTo: '#060405',
      beam: 'hsla(340, 30%, 80%, 0.1)',
      ink: '#db7093'
    },
    Smoky: {
      soft: 'rgba(158, 158, 158, 0.08)',
      softSecondary: 'rgba(158, 158, 158, 0.15)',
      border: 'rgba(158, 158, 158, 0.3)',
      glow: 'rgba(158, 158, 158, 0.25)',
      accent: '#9e9e9e',
      pageFrom: '#121212',
      pageTo: '#080808',
      beam: 'hsla(210, 10%, 65%, 0.15)',
      ink: '#9e9e9e'
    },
    Spicy: {
      soft: 'rgba(178, 34, 34, 0.08)',
      softSecondary: 'rgba(178, 34, 34, 0.15)',
      border: 'rgba(178, 34, 34, 0.3)',
      glow: 'rgba(178, 34, 34, 0.25)',
      accent: '#b22222',
      pageFrom: '#0c0808',
      pageTo: '#060404',
      beam: 'hsla(0, 30%, 75%, 0.1)',
      ink: '#b22222'
    }
  };

  const defaultPalette: FragrancePalette = {
    soft: 'rgba(200, 121, 65, 0.03)',
    softSecondary: 'rgba(200, 121, 65, 0.08)',
    border: 'rgba(200, 121, 65, 0.2)',
    glow: 'rgba(200, 121, 65, 0.15)',
    accent: '#A66336',
    pageFrom: '#0C0B0A',
    pageTo: '#050505',
    beam: 'hsla(25, 20%, 80%, 0.1)',
    ink: '#FDFCFB'
  };

  return palettes[family] || defaultPalette;
}