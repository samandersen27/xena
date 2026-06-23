import { createContext, useContext, useEffect, useState } from 'react'

const DataContext = createContext(null)

export function DataProvider({ children }) {
  const [data, setData]     = useState(null)
  const [states, setStates] = useState([])   // simplified SW states outline
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/xena/data.json').then(r => {
        if (!r.ok) throw new Error(`Could not load data.json (${r.status})`)
        return r.json()
      }),
      fetch('/xena/sw_states.json').then(r => r.ok ? r.json() : []).catch(() => []),
    ])
      .then(([d, st]) => { setData(d); setStates(st); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  return (
    <DataContext.Provider value={{ data, states, loading, error }}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  return useContext(DataContext)
}

// Range polygon for a taxon (by iNat id), or null
export function useRange(inatId) {
  const { data } = useData()
  return data?.ranges?.[String(inatId)] ?? null
}

export function useSwStates() {
  const { states } = useData()
  return states
}

// Convenience selectors
export function useTaxon(inatId) {
  const { data } = useData()
  return data?.taxa?.find(t => String(t.inat_id) === String(inatId)) ?? null
}

export function useObservationsForTaxon(inatId) {
  const { data } = useData()
  return data?.observations?.filter(o => String(o.taxon_inat_id) === String(inatId)) ?? []
}

export function useObservationsForGenus(genus) {
  const { data } = useData()
  const taxonIds = new Set(
    (data?.taxa ?? []).filter(t => t.genus === genus).map(t => t.inat_id)
  )
  return (data?.observations ?? []).filter(o => taxonIds.has(o.taxon_inat_id))
}
