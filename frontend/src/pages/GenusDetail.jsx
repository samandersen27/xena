import { useParams, useNavigate } from 'react-router-dom'
import Nav from '../components/Nav'
import RangeThumb from '../components/RangeThumb'
import { useData, useObservationsForGenus, useSwStates, useRanges } from '../lib/data'

export default function GenusDetail() {
  const { genus }   = useParams()
  const navigate    = useNavigate()
  const { data, loading } = useData()
  const genusObs    = useObservationsForGenus(genus)
  const swStates    = useSwStates()
  const ranges      = useRanges()

  if (loading) return <><Nav /><div className="page loading">Loading…</div></>

  // Species you've actually observed in this genus
  const observedTaxa = (data?.taxa ?? [])
    .filter(t => t.genus === genus)
    .sort((a, b) => (a.name || '').localeCompare(b.name || ''))

  // Master checklist entries for this genus (the 167-species Desert SW list)
  const checklistForGenus = (data?.checklist ?? [])
    .filter(c => c.genus === genus)
    .sort((a, b) => a.name.localeCompare(b.name))

  // Which checklist species are still missing?
  const observedNames = new Set(observedTaxa.map(t => (t.name || '').toLowerCase()))
  const missing = checklistForGenus.filter(
    c => !observedNames.has(c.name.toLowerCase())
  )

  const checklistTotal = checklistForGenus.length

  // Group observations by taxon
  const obsByTaxon = {}
  genusObs.forEach(o => {
    if (!obsByTaxon[o.taxon_inat_id]) obsByTaxon[o.taxon_inat_id] = []
    obsByTaxon[o.taxon_inat_id].push(o)
  })

  return (
    <>
      <Nav />
      <div className="page">
        <div className="back-btn">
          <button className="btn btn-secondary btn-small" onClick={() => navigate(-1)}>← Back</button>
        </div>

        <h1 style={{ fontSize: '1.9rem', fontStyle: 'italic', marginBottom: '0.3rem' }}>{genus}</h1>
        <p style={{ color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.88rem', marginBottom: '1.5rem' }}>
          {observedTaxa.length}{checklistTotal > 0 ? ` of ${checklistTotal}` : ''} species observed
          {genusObs.length > 0 && ` · ${genusObs.length} total observations`}
        </p>

        {/* Observed species */}
        <div className="tile-grid">
          {observedTaxa.map(taxon => {
            const obs     = obsByTaxon[taxon.inat_id] || []
            const photo   = taxon.best_photo
            const states  = [...new Set(obs.map(o => o.state).filter(Boolean))]

            return (
              <div
                key={taxon.inat_id}
                className="tile"
                onClick={() => navigate(`/species/${taxon.inat_id}`)}
              >
                {photo
                  ? <img className="tile-img" src={photo} alt={taxon.name} loading="lazy" />
                  : <div className="tile-no-img">No photo yet</div>
                }
                <div className="tile-body">
                  <div className="tile-name">{taxon.name}</div>
                  {taxon.common_name && <div className="tile-common">{taxon.common_name}</div>}
                  <div className="tile-meta">
                    {obs.length} sighting{obs.length !== 1 ? 's' : ''}
                    {states.length > 0 && ` · ${states.join(', ')}`}
                  </div>
                  {taxon.last_seen && (
                    <div className="tile-meta">Last: {taxon.last_seen}</div>
                  )}
                  <div className="range-thumb-block">
                    <div className="rt-label">Native range</div>
                    <RangeThumb range={ranges.byId[String(taxon.inat_id)] || ranges.byName[(taxon.name||'').toLowerCase()]} states={swStates} />
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Missing species — greyed out, from the master checklist */}
        {missing.length > 0 && (
          <>
            <div className="section-head">
              <h2>Not yet seen</h2>
              <span className="section-count">{missing.length} species</span>
            </div>
            <div className="tile-grid">
              {missing.map(c => (
                <div key={c.name} className="tile dimmed" style={{ cursor: 'default' }}>
                  <div className="tile-no-img">Not yet seen</div>
                  <div className="tile-body">
                    <div className="tile-name">{c.name}</div>
                    {c.common_name && <div className="tile-common">{c.common_name}</div>}
                    <div className="range-thumb-block">
                      <div className="rt-label">Native range</div>
                      <RangeThumb range={ranges.byId[String(c.inat_id)] || ranges.byName[(c.name||'').toLowerCase()]} states={swStates} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </>
  )
}
