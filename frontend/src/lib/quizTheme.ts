export interface FragrancePalette {
  soft: string;
  softSecondary: string;
  border: string;
  glow: string;
  accent: string;
  pageFrom: string;
  pageTo: string;
  beam1: string;
  beam2: string;
  beam3: string;
  beamRaw1: string;
  beamRaw2: string;
  beamRaw3: string;
  ink: string;
  colors: string[];
}

const NOTE_COLORS: Record<string, string> = {
  // Floral
  'white floral': '#FFFFFF',
  'floral': '#E48295',
  'rose': '#FF4D6D',
  'jasmine': '#F8F9FA',
  'iris': '#A29BFE',
  'tuberose': '#FFF9F9',
  
  // Spicy
  'fresh spicy': '#FF6B6B',
  'warm spicy': '#D35400',
  'spicy': '#B22222',
  'pepper': '#7F8C8D',
  'cinnamon': '#A04000',
  
  // Woody
  'woody': '#5D4037',
  'wood': '#8D6E63',
  'cedar': '#4E342E',
  'sandalwood': '#D7CCC8',
  'oud': '#212121',
  
  // Fresh/Aquatic
  'fresh': '#7FCDFF',
  'aquatic': '#4D96FF',
  'marine': '#00B4D8',
  'aromatic': '#2ECC71',
  'citrus': '#FFD93D',
  'lemon': '#FFF338',
  'bergamot': '#C0CA33',
  
  // Fruity
  'fruity': '#FF8A65',
  'fruit': '#FF8A65',
  'peach': '#FFAB91',
  
  // Earthy/Amber
  'amber': '#FFB347',
  'vanilla': '#FFF59D',
  'musky': '#EEEEEE',
  'powdery': '#F8BBD0',
  'earthy': '#4E3629',
  'smoky': '#424242',
  'leather': '#5D4037',
  'green': '#6BCB77',
  'herbal': '#2ECC71',
};

function hexToRgba(hex: string, alpha: number): string {
  if (hex.toLowerCase() === '#ffffff') return `rgba(255, 255, 255, ${alpha})`;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function getFragrancePalette(item: any): FragrancePalette {
  const topNotes = (item?.top_notes || []).map((n: string) => n.toLowerCase());
  const accords = (item?.accords || []).map((a: string) => a.toLowerCase());
  
  const relevantKeywords = Array.from(new Set([...topNotes, ...accords]));
  const matchedColors: string[] = [];
  
  for (const keyword of relevantKeywords) {
    for (const [note, color] of Object.entries(NOTE_COLORS)) {
      if (keyword.includes(note)) {
        if (!matchedColors.includes(color)) {
          matchedColors.push(color);
        }
        break;
      }
    }
    if (matchedColors.length >= 3) break;
  }

  // Fallback cascade
  const c1 = matchedColors[0] || '#A66336';
  const c2 = matchedColors[1] || c1;
  const c3 = matchedColors[2] || c2;

  const createBeam = (color: string) => `linear-gradient(180deg, 
    ${hexToRgba(color, 0)} 0%, 
    ${hexToRgba(color, 0.5)} 20%, 
    ${hexToRgba(color, 0.7)} 50%, 
    ${hexToRgba(color, 0.5)} 80%, 
    ${hexToRgba(color, 0)} 100%
  )`;

  return {
    soft: hexToRgba(c1, 0.08),
    softSecondary: hexToRgba(c1, 0.15),
    border: hexToRgba(c1, 0.5),
    glow: hexToRgba(c1, 0.35),
    accent: c1,
    pageFrom: '#080808',
    pageTo: '#040404',
    beam1: createBeam(c1),
    beam2: createBeam(c2),
    beam3: createBeam(c3),
    beamRaw1: hexToRgba(c1, 0.6),
    beamRaw2: hexToRgba(c2, 0.6),
    beamRaw3: hexToRgba(c3, 0.6),
    ink: '#FDFCFB',
    colors: [c1, c2, c3]
  };
}