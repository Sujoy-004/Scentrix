'use client'

import { Suspense, useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { FragranceCard } from '@/components/FragranceCard'
import { BrowseFilters } from '@/components/BrowseFilters'
import { api } from '@/lib/api'
import './fragrances.css'

const LIMIT = 24

function FragrancesContent() {
  const searchParams = useSearchParams()

  const family = searchParams.get('family') || undefined
  const query = searchParams.get('q') || undefined
  const brand = searchParams.get('brand') || undefined
  const concentration = searchParams.get('concentration') || undefined
  const sort = searchParams.get('sort') || undefined

  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [initialLoading, setInitialLoading] = useState(true)

  const loadData = useCallback(async (reset = false) => {
    if (loading) return
    setLoading(true)

    const currentOffset = reset ? 0 : offset

    const res = await api.getFragranceCatalog(
      LIMIT,
      currentOffset,
      { family, q: query, brand, sort }
    )

    const responseData = res.data || res
    const items = responseData.items || []
    const newTotal = responseData.total ?? 0

    setTotal(newTotal)
    setData(prev => reset ? items : [...prev, ...items])
    setOffset(prev => reset ? LIMIT : prev + LIMIT)
    setHasMore(items.length === LIMIT)

    setLoading(false)
    setInitialLoading(false)
  }, [family, query, brand, sort, offset, loading])

  useEffect(() => {
    setInitialLoading(true)
    setData([])
    setOffset(0)
    setHasMore(true)
    loadData(true)
  }, [family, query, brand, sort])

  return (
    <div className="browse-page">
      <div className="container mx-auto px-6">

        <header className="browse-header">
          <h1 className="font-display italic text-white">
            {family ? (
              <span className="capitalize">{family}</span>
            ) : (
              'Discover Fragrances'
            )}
          </h1>
          <p className="text-sm text-white/50">
            Explore by family, note, or brand
          </p>
        </header>

        <BrowseFilters total={total} loading={loading} />

        <div className="mt-10">
          {initialLoading ? (
            <div className="text-white/40 text-center py-20 text-sm">Loading fragrances…</div>
          ) : data.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-white/40 text-sm">No fragrances match your filters.</p>
              <button
                onClick={() => window.location.href = '/fragrances'}
                className="mt-4 text-xs font-bold uppercase tracking-wider text-amber-400 hover:text-amber-300 transition-colors"
              >
                Clear filters
              </button>
            </div>
          ) : (
            <>
              <AnimatePresence mode="wait">
                <motion.div
                  key={[family, query, brand, sort].join('|')}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
                >
                  {data.map((frag, index) => (
                    <FragranceCard
                      key={frag.id}
                      frag={frag}
                      index={index}
                    />
                  ))}
                </motion.div>
              </AnimatePresence>

              {hasMore && (
                <div className="flex justify-center mt-10">
                  <button
                    onClick={() => loadData(false)}
                    disabled={loading}
                    className="px-8 py-3 border border-white/20 rounded-xl text-white/70 text-sm hover:bg-white/[0.06] transition disabled:opacity-40"
                  >
                    {loading ? 'Loading…' : 'Load More'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>

      </div>
    </div>
  )
}

export default function FragrancesPage() {
  return (
    <Suspense fallback={
      <div className="browse-page">
        <div className="container mx-auto px-6">
          <div className="text-white/40 text-center py-20 text-sm">Loading fragrances…</div>
        </div>
      </div>
    }>
      <FragrancesContent />
    </Suspense>
  )
}
