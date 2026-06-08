'use client';

import { useCallback, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Search, X, ChevronDown, ChevronUp } from 'lucide-react';

const FAMILIES = [
  'Floral', 'Woody', 'Citrus', 'Oriental', 'Amber', 'Smoky',
  'Fruity', 'Gourmand', 'Leather', 'Spicy', 'Aquatic', 'Aromatic',
  'Green', 'Musky', 'Powdery', 'Earthy', 'Animalic', 'Fresh',
];

const CONCENTRATIONS = ['All', 'EDP', 'EDT', 'Parfum', 'Cologne'];

const SORT_OPTIONS = [
  { value: '', label: 'Most Relevant' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'name', label: 'Name A–Z' },
];

const FAMILIES_SHOWN = 6;

interface BrowseFiltersProps {
  total: number;
  loading?: boolean;
}

export function BrowseFilters({ total, loading }: BrowseFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const family = searchParams.get('family') || '';
  const query = searchParams.get('q') || '';
  const brand = searchParams.get('brand') || '';
  const concentration = searchParams.get('concentration') || '';
  const sort = searchParams.get('sort') || '';

  const [familiesOpen, setFamiliesOpen] = useState(false);

  const updateParam = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      router.push(`/fragrances?${params.toString()}`);
    },
    [router, searchParams],
  );

  const clearFilters = useCallback(() => {
    router.push('/fragrances');
  }, [router]);

  const hasActiveFilters = useMemo(
    () => !!(family || query || brand || concentration || sort),
    [family, query, brand, concentration, sort],
  );

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (family) count++;
    if (query) count++;
    if (brand) count++;
    if (concentration) count++;
    return count;
  }, [family, query, brand, concentration]);

  const visibleFamilies = familiesOpen ? FAMILIES : FAMILIES.slice(0, FAMILIES_SHOWN);
  const hiddenCount = FAMILIES.length - FAMILIES_SHOWN;

  return (
    <div className="browse-filters">
      {/* Level 2: Search */}
      <div className="relative">
        <Search
          size={16}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-white/25 pointer-events-none"
        />
        <input
          type="text"
          placeholder="Search fragrances, notes, or accords…"
          value={query}
          onChange={(e) => updateParam('q', e.target.value)}
          className="w-full bg-white/[0.03] border border-white/8 rounded-2xl pl-12 pr-10 py-3.5 text-sm text-white/80 placeholder:text-white/25 outline-none focus:border-amber-500/30 focus:bg-white/[0.05] transition-all"
        />
        {query && (
          <button
            onClick={() => updateParam('q', '')}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/50 transition-colors"
          >
            <X size={15} />
          </button>
        )}
      </div>

      {/* Level 3: Filter controls row */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-3 flex-1">
          {/* Brand */}
          <div className="relative flex-1 sm:max-w-52">
            <input
              type="text"
              placeholder="Brand"
              value={brand}
              onChange={(e) => updateParam('brand', e.target.value)}
              className="w-full bg-white/[0.02] border border-white/8 rounded-xl px-4 py-2.5 text-sm text-white/70 placeholder:text-white/25 outline-none focus:border-amber-500/30 focus:bg-white/[0.04] transition-all"
            />
            {brand && (
              <button
                onClick={() => updateParam('brand', '')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/50"
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Sort */}
          <div className="relative">
            <select
              value={sort}
              onChange={(e) => updateParam('sort', e.target.value)}
              className="appearance-none bg-white/[0.02] border border-white/8 rounded-xl pl-4 pr-9 py-2.5 text-sm text-white/70 outline-none focus:border-amber-500/30 focus:bg-white/[0.04] transition-all cursor-pointer min-w-[9rem]"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-[#0a0a0a] text-white/80">
                  {opt.label}
                </option>
              ))}
            </select>
            <ChevronDown
              size={13}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-white/25 pointer-events-none"
            />
          </div>
        </div>

        {/* Clear + count */}
        <div className="flex items-center gap-3 shrink-0 self-start sm:self-auto">
          {loading && (
            <span className="text-[10px] text-white/30 uppercase tracking-widest animate-pulse">
              Loading…
            </span>
          )}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-[10px] font-bold uppercase tracking-wider text-white/30 hover:text-white/60 transition-colors"
            >
              Clear ({activeFilterCount})
            </button>
          )}
        </div>
      </div>

      {/* Level 4: Families */}
      <div className="browse-families-section">
        <button
          onClick={() => setFamiliesOpen(!familiesOpen)}
          className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-white/30 hover:text-white/50 transition-colors"
        >
          {family && (
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400/70" />
          )}
          Families
          <span className="text-white/15 font-mono text-[9px]">{FAMILIES.length}</span>
          {familiesOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        <div className="browse-families-pills">
          {visibleFamilies.map((f) => {
            const active = family.toLowerCase() === f.toLowerCase();
            return (
              <button
                key={f}
                onClick={() => updateParam('family', active ? '' : f.toLowerCase())}
                className={`browse-family-pill ${
                  active
                    ? 'browse-family-pill--active'
                    : 'browse-family-pill--inactive'
                }`}
              >
                {f}
              </button>
            );
          })}
          {!familiesOpen && hiddenCount > 0 && (
            <button
              onClick={() => setFamiliesOpen(true)}
              className="browse-family-pill browse-family-pill--more"
            >
              +{hiddenCount} more
            </button>
          )}
        </div>
      </div>

      {/* Level 5: Concentration */}
      <div className="flex items-center gap-2">
        <span className="text-[9px] font-bold uppercase tracking-widest text-white/20">Conc.</span>
        {CONCENTRATIONS.map((c) => {
          const active = c === 'All' ? !concentration : concentration.toLowerCase() === c.toLowerCase();
          return (
            <button
              key={c}
              onClick={() => updateParam('concentration', c === 'All' ? '' : c.toLowerCase())}
              className={`browse-conc-pill ${
                active
                  ? 'browse-conc-pill--active'
                  : 'browse-conc-pill--inactive'
              }`}
            >
              {c}
            </button>
          );
        })}
      </div>
    </div>
  );
}
