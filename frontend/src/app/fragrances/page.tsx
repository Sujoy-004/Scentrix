'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { FragranceCard } from '@/components/FragranceCard'
import { FragranceFamilies } from '@/components/FragranceFamilies'
import { api } from '@/lib/api'

export default function FragrancesPage() {
  const searchParams = useSearchParams()

  const family = searchParams.get('family') || undefined
  const query = searchParams.get('q') || undefined

  const [data, setData] = useState<any[]>([])
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)

  const LIMIT = 24

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
  }

  // reload on filter change
  useEffect(() => {
    if (!family && !query) return

    loadData(true)
  }, [family, query])

  return (
    <div className="p-6 space-y-10">

      {/* STATE 1: NO FAMILY SELECTED */}
      {!family && (
        <div className="space-y-10">
          <div className="text-center space-y-4">
            <h1 className="text-4xl md:text-5xl font-serif italic text-white">
              Choose a Family to Begin
            </h1>
            <p className="text-white/60">
              Each family holds a universe of scents waiting to be discovered
            </p>
          </div>

          <FragranceFamilies />
        </div>
      )}

      {/* STATE 2: FAMILY SELECTED */}
      {family && (
        <div className="space-y-8">

          <div className="flex justify-between items-center">
            <button
              onClick={() => window.location.href = '/fragrances'}
              className="text-white/60 hover:text-white"
            >
              ← Back to families
            </button>

            <div className="text-white capitalize text-xl">
              {family}
            </div>
          </div>

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
                className="px-6 py-3 border border-white/20 rounded-xl text-white hover:bg-white/10 transition"
              >
                Load More
              </button>
            </div>
          )}
        </div>
      )}

    </div>
  )
}