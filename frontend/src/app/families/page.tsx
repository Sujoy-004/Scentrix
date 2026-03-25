'use client';

import { useRouter } from 'next/navigation';
import { getFragranceFamilies } from '@/lib/mockData';
import './families.css';

export default function FamiliesPage() {
  const router = useRouter();
  const families = getFragranceFamilies();

  const familyEmojis: Record<string, string> = {
    woody: '🌲',
    citrus: '🍊',
    aromatic: '🌿',
    spicy: '🌶',
    floral: '🌸',
    fresh: '💧',
    fruity: '🍓',
    oriental: '✨',
  };

  const familyDescriptions: Record<string, string> = {
    woody: 'Rich, warm, and grounding fragrances with deep base notes of sandalwood, cedar, and vetiver.',
    citrus: 'Bright, fresh, and energizing scents with zesty top notes of bergamot, lemon, and orange.',
    aromatic: 'Fresh, herbal, and invigorating fragrances featuring lavender, rosemary, and mint.',
    spicy: 'Warm, exotic, and sensual scents with pepper, cinnamon, and cardamom notes.',
    floral: 'Delicate, romantic, and elegant fragrances celebrating flowers like roses and jasmine.',
    fresh: 'Light, airy, and refreshing scents that evoke the ocean and cool breeze.',
    fruity: 'Juicy, playful, and vibrant fragrances bursting with apple, peach, and berry notes.',
    oriental: 'Sweet, sensual, and warm scents with vanilla, tonka bean, and amber notes.',
  };

  return (
    <div className="families-page">
      <div className="families-container">
        {/* Header */}
        <div className="families-header">
          <h1>Fragrance Families</h1>
          <p>Explore fragrances by their signature characteristics and scent profiles</p>
        </div>

        {/* Families Grid */}
        <div className="families-grid">
          {families.map((family: string) => (
            <div
              key={family}
              className="family-card"
              onClick={() => router.push(`/families/${family}`)}
            >
              <div className="family-emoji">
                {familyEmojis[family.toLowerCase()] || '🧴'}
              </div>

              <div className="family-content">
                <h2 className="family-name">
                  {family.charAt(0).toUpperCase() + family.slice(1)}
                </h2>

                <p className="family-description">
                  {familyDescriptions[family.toLowerCase()] || `Discover ${family} fragrances`}
                </p>

                <button className="family-explore-btn">
                  Explore → 
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
