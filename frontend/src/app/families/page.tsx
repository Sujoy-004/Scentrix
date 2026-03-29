'use client';

import { useRouter } from 'next/navigation';
import './families.css';

const FAMILIES = [
  { id: 'floral',   name: 'Floral',   description: 'Delicate, romantic, and elegant fragrances celebrating flowers like roses and jasmine.' },
  { id: 'woody',    name: 'Woody',    description: 'Rich, warm, and grounding fragrances with deep base notes of sandalwood, cedar, and vetiver.' },
  { id: 'citrus',   name: 'Citrus',   description: 'Bright, fresh, and energizing scents with zesty top notes of bergamot, lemon, and orange.' },
  { id: 'amber',    name: 'Amber',    description: 'Sweet, sensual, and warm scents with vanilla, tonka bean, and amber notes.' },
  { id: 'aromatic', name: 'Aromatic', description: 'Fresh, herbal, and invigorating fragrances featuring lavender, rosemary, and mint.' },
  { id: 'fruity',   name: 'Fruity',   description: 'Juicy, playful, and vibrant fragrances bursting with apple, peach, and berry notes.' },
  { id: 'chypre',   name: 'Chypré',   description: 'Classic, elegant, and timeless fragrances blending citrus, florals, and woody base notes.' },
  { id: 'aquatic',  name: 'Aquatic',  description: 'Light, airy, and refreshing scents that evoke the ocean and cool breeze.' },
];

const FAMILY_EMOJIS: Record<string, string> = {
  floral: '🌸', woody: '🌲', citrus: '🍊', amber: '🍯',
  aromatic: '🌿', fruity: '🍓', chypre: '✨', aquatic: '💧',
};

export default function FamiliesPage() {
  const router = useRouter();

  return (
    <div className="families-page">
      <div className="families-container">
        <div className="families-header">
          <h1>Fragrance Families</h1>
          <p>Find your scent profile across these carefully curated families</p>
        </div>

        <div className="families-grid">
          {FAMILIES.map((family) => (
            <div
              key={family.id}
              className="family-card"
              onClick={() => router.push(`/families/${family.id}`)}
            >
              <div className="family-emoji">
                {FAMILY_EMOJIS[family.id] || '🧴'}
              </div>
              <div className="family-content">
                <h2 className="family-name">{family.name}</h2>
                <p className="family-description">{family.description}</p>
                <button className="family-explore-btn">Explore →</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
