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
  const family = typeof item === 'string' ? item : (item?.family || 'Default');
  
  const palettes: Record<string, FragrancePalette> = {
    Woody: {
      soft: 'rgba(60, 42, 33, 0.03)',
      softSecondary: 'rgba(60, 42, 33, 0.08)',
      border: 'rgba(160, 120, 90, 0.2)',
      glow: 'rgba(160, 120, 90, 0.15)',
      accent: '#8B5E3C',
      pageFrom: '#FDFCFB',
      pageTo: '#F5F2F0',
      beam: 'hsla(30, 20%, 80%, 0.1)',
      ink: '#2A1A12'
    },
    Fresh: {
      soft: 'rgba(215, 235, 245, 0.3)',
      softSecondary: 'rgba(215, 235, 245, 0.5)',
      border: 'rgba(96, 160, 217, 0.2)',
      glow: 'rgba(96, 160, 217, 0.15)',
      accent: '#4A90E2',
      pageFrom: '#F7FBFE',
      pageTo: '#EEF4F9',
      beam: 'hsla(210, 30%, 90%, 0.2)',
      ink: '#0F2D4A'
    },
    Oriental: {
      soft: 'rgba(224, 128, 192, 0.05)',
      softSecondary: 'rgba(224, 128, 192, 0.1)',
      border: 'rgba(224, 128, 192, 0.2)',
      glow: 'rgba(224, 128, 192, 0.15)',
      accent: '#B04080',
      pageFrom: '#FFF5FA',
      pageTo: '#F8E8F2',
      beam: 'hsla(320, 20%, 85%, 0.1)',
      ink: '#3D102A'
    },
    Chypre: {
      soft: 'rgba(118, 197, 118, 0.05)',
      softSecondary: 'rgba(118, 197, 118, 0.1)',
      border: 'rgba(118, 197, 118, 0.2)',
      glow: 'rgba(118, 197, 118, 0.15)',
      accent: '#4A8B4A',
      pageFrom: '#F7FFF7',
      pageTo: '#EFF6EF',
      beam: 'hsla(120, 20%, 85%, 0.1)',
      ink: '#1A331A'
    },
    Floral: {
      soft: 'rgba(228, 160, 176, 0.05)',
      softSecondary: 'rgba(228, 160, 176, 0.1)',
      border: 'rgba(228, 160, 176, 0.2)',
      glow: 'rgba(228, 160, 176, 0.15)',
      accent: '#D17C8C',
      pageFrom: '#FFF9FA',
      pageTo: '#F9F0F2',
      beam: 'hsla(345, 30%, 90%, 0.1)',
      ink: '#4A2A2F'
    },
    Amber: {
      soft: 'rgba(196, 113, 0, 0.04)',
      softSecondary: 'rgba(196, 113, 0, 0.09)',
      border: 'rgba(196, 113, 0, 0.2)',
      glow: 'rgba(196, 113, 0, 0.12)',
      accent: '#C47100',
      pageFrom: '#FFFAF0',
      pageTo: '#F9F3E8',
      beam: 'hsla(35, 30%, 85%, 0.12)',
      ink: '#4A2B00'
    },
    Animalic: {
      soft: 'rgba(84, 71, 53, 0.04)',
      softSecondary: 'rgba(84, 71, 53, 0.09)',
      border: 'rgba(84, 71, 53, 0.3)',
      glow: 'rgba(84, 71, 53, 0.15)',
      accent: '#544735',
      pageFrom: '#F9F8F6',
      pageTo: '#F1EFE9',
      beam: 'hsla(30, 15%, 80%, 0.1)',
      ink: '#2A231A'
    },
    Aquatic: {
      soft: 'rgba(127, 205, 255, 0.06)',
      softSecondary: 'rgba(127, 205, 255, 0.12)',
      border: 'rgba(127, 205, 255, 0.3)',
      glow: 'rgba(127, 205, 255, 0.2)',
      accent: '#007ACC',
      pageFrom: '#F4FAFF',
      pageTo: '#E8F5FF',
      beam: 'hsla(200, 40%, 92%, 0.25)',
      ink: '#003A61'
    },
    Aromatic: {
      soft: 'rgba(0, 155, 119, 0.03)',
      softSecondary: 'rgba(0, 155, 119, 0.08)',
      border: 'rgba(0, 155, 119, 0.25)',
      glow: 'rgba(0, 155, 119, 0.15)',
      accent: '#009B77',
      pageFrom: '#F2FCF9',
      pageTo: '#EAF7F2',
      beam: 'hsla(160, 25%, 88%, 0.15)',
      ink: '#003D2E'
    },
    Citrus: {
      soft: 'rgba(255, 184, 28, 0.05)',
      softSecondary: 'rgba(255, 184, 28, 0.1)',
      border: 'rgba(255, 184, 28, 0.3)',
      glow: 'rgba(255, 184, 28, 0.2)',
      accent: '#FFB81C',
      pageFrom: '#FFFDF2',
      pageTo: '#FFF9E0',
      beam: 'hsla(45, 50%, 92%, 0.2)',
      ink: '#4A3500'
    },
    Earthy: {
      soft: 'rgba(111, 78, 55, 0.04)',
      softSecondary: 'rgba(111, 78, 55, 0.09)',
      border: 'rgba(111, 78, 55, 0.3)',
      glow: 'rgba(111, 78, 55, 0.15)',
      accent: '#6F4E37',
      pageFrom: '#F9F7F5',
      pageTo: '#EFEAE6',
      beam: 'hsla(25, 15%, 82%, 0.1)',
      ink: '#35251A'
    },
    Gourmand: {
      soft: 'rgba(210, 105, 30, 0.04)',
      softSecondary: 'rgba(210, 105, 30, 0.09)',
      border: 'rgba(210, 105, 30, 0.2)',
      glow: 'rgba(210, 105, 30, 0.12)',
      accent: '#D2691E',
      pageFrom: '#FFF9F5',
      pageTo: '#F9F1E8',
      beam: 'hsla(25, 25%, 85%, 0.1)',
      ink: '#4A250B'
    },
    Green: {
      soft: 'rgba(86, 130, 3, 0.03)',
      softSecondary: 'rgba(86, 130, 3, 0.08)',
      border: 'rgba(86, 130, 3, 0.25)',
      glow: 'rgba(86, 130, 3, 0.15)',
      accent: '#568203',
      pageFrom: '#F7FCF2',
      pageTo: '#EEF6E8',
      beam: 'hsla(90, 20%, 88%, 0.15)',
      ink: '#233201'
    },
    Leather: {
      soft: 'rgba(74, 42, 27, 0.05)',
      softSecondary: 'rgba(74, 42, 27, 0.1)',
      border: 'rgba(74, 42, 27, 0.3)',
      glow: 'rgba(74, 42, 27, 0.15)',
      accent: '#4A2A1B',
      pageFrom: '#F9F7F6',
      pageTo: '#F2EDEB',
      beam: 'hsla(15, 20%, 75%, 0.1)',
      ink: '#1A0F09'
    },
    Musky: {
      soft: 'rgba(220, 212, 195, 0.1)',
      softSecondary: 'rgba(220, 212, 195, 0.2)',
      border: 'rgba(180, 172, 155, 0.3)',
      glow: 'rgba(180, 172, 155, 0.2)',
      accent: '#C0B6A1',
      pageFrom: '#FBFBFA',
      pageTo: '#F7F6F4',
      beam: 'hsla(45, 10%, 93%, 0.1)',
      ink: '#3D3A33'
    },
    Powdery: {
      soft: 'rgba(255, 240, 245, 0.3)',
      softSecondary: 'rgba(255, 240, 245, 0.5)',
      border: 'rgba(219, 112, 147, 0.2)',
      glow: 'rgba(219, 112, 147, 0.15)',
      accent: '#DB7093',
      pageFrom: '#FFFBFC',
      pageTo: '#FAF2F5',
      beam: 'hsla(340, 30%, 94%, 0.2)',
      ink: '#4A2631'
    },
    Smoky: {
      soft: 'rgba(54, 69, 79, 0.05)',
      softSecondary: 'rgba(54, 69, 79, 0.1)',
      border: 'rgba(54, 69, 79, 0.3)',
      glow: 'rgba(54, 69, 79, 0.2)',
      accent: '#36454F',
      pageFrom: '#F6F7F8',
      pageTo: '#E8EAED',
      beam: 'hsla(210, 10%, 75%, 0.15)',
      ink: '#1A2126'
    },
    Spicy: {
      soft: 'rgba(178, 34, 34, 0.04)',
      softSecondary: 'rgba(178, 34, 34, 0.09)',
      border: 'rgba(178, 34, 34, 0.2)',
      glow: 'rgba(178, 34, 34, 0.15)',
      accent: '#B22222',
      pageFrom: '#FFF5F5',
      pageTo: '#F9E8E8',
      beam: 'hsla(0, 30%, 88%, 0.1)',
      ink: '#4A0F0F'
    }
  };

  const defaultPalette: FragrancePalette = {
    soft: 'rgba(200, 121, 65, 0.03)',
    softSecondary: 'rgba(200, 121, 65, 0.08)',
    border: 'rgba(200, 121, 65, 0.2)',
    glow: 'rgba(200, 121, 65, 0.15)',
    accent: '#A66336',
    pageFrom: '#FDFCFB',
    pageTo: '#F8F5F2',
    beam: 'hsla(25, 20%, 80%, 0.1)',
    ink: '#331D0E'
  };

  return palettes[family] || defaultPalette;
}