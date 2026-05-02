'use client'

import { useEffect, useState } from 'react'

type Fragrance = {
  id: number
  name: string
  brand: string
  family?: string
}

export default function FragrancesPage() {
  const [data, setData] = useState<Fragrance[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchFragrances = async () => {
      try {
        // CHANGE this to your actual backend endpoint
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/fragrances`)

        if (!res.ok) throw new Error('Failed to fetch')

        const json = await res.json()
        setData(json)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchFragrances()
  }, [])

  if (loading) return <div style={{ padding: 24 }}>Loading...</div>
  if (error) return <div style={{ padding: 24 }}>Error: {error}</div>

  return (
    <div style={{ padding: 24 }}>
      <h1>Fragrance Catalog</h1>

      {data.length === 0 ? (
        <p>No fragrances found.</p>
      ) : (
        <div style={{ display: 'grid', gap: 16 }}>
          {data.map((f) => (
            <div key={f.id} style={{ border: '1px solid #ccc', padding: 12 }}>
              <h3>{f.name}</h3>
              <p>{f.brand}</p>
              {f.family && <p>{f.family}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}