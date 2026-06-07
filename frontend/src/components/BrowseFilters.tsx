'use client';

import { useCallback, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Search, X, ChevronDown } from 'lucide-react';

const FAMILIES = [
  'Floral', 'Woody', 'Citrus', 'Oriental', 'Amber', 'Smoky',
  'Fruity', 'Gourmand', 'Leather', 'Spicy', 'Aquatic', 'Aromatic',
  'Green', 'Musky', 'Powdery', 'Earthy', 'Animalic', 'Fresh',
];

const CONCENTRATIONS = ['All', 'EDP', 'EDT', 'Parfum', 'Cologne'];

const SORT_OPTIONS = [
  { value: '', label: 'Default' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'name', label: 'Name A–Z' },
];

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

  return (
    <div className="space-y-6">
      {/* Search + Brand row */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none"
          />
          <input
            type="text"
            placeholder="Search fragrances, notes, accords…"
            value={query}
            onChange={(e) => updateParam('q', e.target.value)}
            className="w-full bg-white/[0.04] border border-white/10 rounded-xl pl-11 pr-4 py-3 text-sm text-white/80 placeholder:text-white/30 outline-none focus:border-amber-500/40 focus:bg-white/[0.06] transition-all"
          />
          {query && (
            <button
              onClick={() => updateParam('q', '')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <input
          type="text"
          placeholder="Brand…"
          value={brand}
          onChange={(e) => updateParam('brand', e.target.value)}
          className="w-full sm:w-44 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-3 text-sm text-white/80 placeholder:text-white/30 outline-none focus:border-amber-500/40 focus:bg-white/[0.06] transition-all"
        />
        <div className="relative">
          <select
            value={sort}
            onChange={(e) => updateParam('sort', e.target.value)}
            className="appearance-none w-full sm:w-40 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-3 pr-10 text-sm text-white/80 outline-none focus:border-amber-500/40 focus:bg-white/[0.06] transition-all cursor-pointer"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-[#0a0a0a]">
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown
            size={14}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none"
          />
        </div>
      </div>

      {/* Family pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
        {FAMILIES.map((f) => {
          const active = family.toLowerCase() === f.toLowerCase();
          return (
            <button
              key={f}
              onClick={() => updateParam('family', active ? '' : f.toLowerCase())}
              className={`shrink-0 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                active
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-white/[0.04] text-white/50 border border-white/10 hover:bg-white/[0.08] hover:text-white/70'
              }`}
            >
              {f}
            </button>
          );
        })}
      </div>

      {/* Concentration pills + total count row */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {CONCENTRATIONS.map((c) => {
            const active = c === 'All' ? !concentration : concentration.toLowerCase() === c.toLowerCase();
            return (
              <button
                key={c}
                onClick={() => updateParam('concentration', c === 'All' ? '' : c.toLowerCase())}
                className={`shrink-0 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all ${
                  active
                    ? 'bg-white/10 text-white border border-white/20'
                    : 'bg-white/[0.03] text-white/40 border border-white/5 hover:bg-white/[0.06]'
                }`}
              >
                {c}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {loading && (
            <span className="text-[10px] text-white/40 uppercase tracking-widest animate-pulse">
              Loading…
            </span>
          )}
          <span className="text-xs text-white/50 font-bold tracking-wider">
            {total} fragrance{total !== 1 ? 's' : ''}
          </span>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-[10px] font-bold uppercase tracking-wider text-white/30 hover:text-white/60 transition-colors"
            >
              Clear all
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
