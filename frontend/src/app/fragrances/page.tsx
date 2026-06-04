'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { FragranceCard } from '@/components/FragranceCard'
import { api } from '@/lib/api'

const LIMIT = 24

function FragrancesContent() {
  const searchParams = useSearchParams()

  const family = searchParams.get('family') || undefined
  const query = searchParams.get('q') || undefined

  const [data, setData] = useState<any[]>([])
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [initialLoading, setInitialLoading] = useState(true)

  const loadData = async (reset = false) => {
    if (loading) return
    setLoading(true)

    const currentOffset = reset ? 0 : offset

    const res = await api.getFragranceCatalog(
      LIMIT,
      currentOffset,
      { family, q: query }
    )

    const items = res.items || []

    setData(prev => reset ? items : [...prev, ...items])
    setOffset(prev => reset ? LIMIT : prev + LIMIT)
    setHasMore(items.length === LIMIT)

    setLoading(false)
    setInitialLoading(false)
  }

  useEffect(() => {
    loadData(true)
  }, [family, query])

  return (
    <div className="p-6 space-y-10">

      <div className="space-y-8">

        <div className="flex justify-between items-center">
          <h1 className="text-3xl md:text-4xl font-serif italic text-white">
            {family ? (
              <span className="capitalize">{family}</span>
            ) : (
              'Browse All Fragrances'
            )}
          </h1>
        </div>

        {initialLoading ? (
          <div className="text-white/60 text-center py-20">Loading fragrances...</div>
        ) : data.length === 0 ? (
          <div className="text-white/60 text-center py-20">
            {family
              ? `No fragrances found in the "${family}" family.`
              : 'No fragrances found.'}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {data.map((frag, index) => (
                <FragranceCard
                  key={frag.id}
                  frag={frag}
                  index={index}
                />
              ))}
            </div>

            {hasMore && (
              <div className="flex justify-center">
                <button
                  onClick={() => loadData()}
                  disabled={loading}
                  className="px-6 py-3 border border-white/20 rounded-xl text-white hover:bg-white/10 transition disabled:opacity-50"
                >
                  {loading ? 'Loading...' : 'Load More'}
                </button>
              </div>
            )}
          </>
        )}

      </div>

    </div>
  )
}

export default function FragrancesPage() {
  return (
    <Suspense fallback={
      <div className="p-6 text-white/60 text-center py-20">Loading fragrances...</div>
    }>
      <FragrancesContent />
    </Suspense>
  )
}
