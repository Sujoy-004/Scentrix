export function getFragrancePalette(family: string): { primary: string; secondary: string; bg: string } {
  const palettes: Record<string, { primary: string; secondary: string; bg: string }> = {
    Woody:    { primary: '#a0785a', secondary: '#c8a882', bg: 'rgba(160,120,90,0.1)' },
    Fresh:    { primary: '#60a0d9', secondary: '#a0d0f0', bg: 'rgba(96,160,217,0.1)' },
    Oriental: { primary: '#e080c0', secondary: '#f0b0d8', bg: 'rgba(224,128,192,0.1)' },
    Chypre:   { primary: '#76c576', secondary: '#b0e0b0', bg: 'rgba(118,197,118,0.1)' },
    Floral:   { primary: '#e4a0b0', secondary: '#f8d0d8', bg: 'rgba(228,160,176,0.1)' },
  };
  return palettes[family] || { primary: '#c87941', secondary: '#e4c285', bg: 'rgba(200,121,65,0.1)' };
}