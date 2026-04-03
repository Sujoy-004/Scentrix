'use client';

import { useRouter } from 'next/navigation';

export function FragranceFamilies() {
  const router = useRouter();

  const families = [
    { name: 'Floral', slug: 'floral', notes: 'Roses, jasmine, lily', description: 'Delicate and feminine' },
    { name: 'Woody', slug: 'woody', notes: 'Sandalwood, cedar, vetiver', description: 'Rich and warm' },
    { name: 'Citrus', slug: 'citrus', notes: 'Bergamot, lemon, orange', description: 'Bright and energizing' },
    { name: 'Amber', slug: 'amber', notes: 'Vanilla, tonka bean, musk', description: 'Sweet and sensual' },
    { name: 'Aromatic', slug: 'aromatic', notes: 'Lavender, rosemary, mint', description: 'Fresh and herbal' },
    { name: 'Fruity', slug: 'fruity', notes: 'Apple, peach, berries', description: 'Juicy and playful' },
    { name: 'Aquatic', slug: 'aquatic', notes: 'Marine, ozonic, fresh', description: 'Light and airy' },
    { name: 'Gourmand', slug: 'gourmand', notes: 'Caramel, chocolate, vanilla', description: 'Edible and delicious' },
    { name: 'Animalic', slug: 'animalic', notes: 'Civet, musk, honey', description: 'Primal and deep' },
    { name: 'Earthy', slug: 'earthy', notes: 'Patchouli, moss, soil', description: 'Natural and grounded' },
    { name: 'Fresh', slug: 'fresh', notes: 'Aldehydes, citrus, water', description: 'Clean and crisp' },
    { name: 'Green', slug: 'green', notes: 'Grass, leaves, galbanum', description: 'Verdant and lush' },
    { name: 'Leather', slug: 'leather', notes: 'Birch tar, saffron, skin', description: 'Sophisticated and bold' },
    { name: 'Musky', slug: 'musky', notes: 'White musk, ambrette', description: 'Soft and intimate' },
    { name: 'Oriental', slug: 'oriental', notes: 'Oud, spices, resins', description: 'Exotic and mysterious' },
    { name: 'Powdery', slug: 'powdery', notes: 'Iris, violet, orris', description: 'Classic and refined' },
    { name: 'Smoky', slug: 'smoky', notes: 'Incense, tobacco, leather', description: 'Atmospheric and dark' },
    { name: 'Spicy', slug: 'spicy', notes: 'Cinnamon, pepper, ginger', description: 'Warm and vibrant' },
  ];

  return (
    <section className="fragrance-families scroll-reveal">
      <div className="fragrance-families-container">
        <div className="section-header families-header">
          <h2 className="section-title" string="split" string-repeat="true" string-split="word">Explore Fragrance Families</h2>
          <p className="section-subtitle" string="split" string-repeat="true" string-split="word">Find your scent profile across these carefully curated families</p>
        </div>

        <div className="elite-grid-container">
          {families.slice(0, 10).map((family, index) => (
            <div 
              key={index} 
              className="elite-family-card glass-card scroll-reveal" 
              style={{ '--stagger-index': index } as any}
              onClick={() => router.push(`/fragrances?family=${family.slug}`)}
            >
              <div className="elite-card-bg">
                <img 
                  src={`/assets/families/${family.slug}.png`} 
                  alt={family.name} 
                  className="elite-bg-img"
                  loading="lazy"
                />
                <div className="elite-card-overlay"></div>
              </div>
              
              <div className="elite-card-content">
                <h3 className="family-name text-gradient-amber">{family.name}</h3>
                <p className="family-description">{family.description}</p>
                <button className="family-btn-minimal">
                  Explore
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="families-footer">
          <button 
            className="btn btn-outline show-more-btn scroll-reveal"
            onClick={() => router.push('/fragrances')}
          >
            Explore All 18 Families
          </button>
        </div>
      </div>
    </section>
  );
}
