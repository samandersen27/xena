import { useNavigate } from 'react-router-dom'
import Nav from '../components/Nav'
import { useData } from '../lib/data'

function ProgressBar({ pct }) {
  return (
    <div className="progress-track">
      <div className="progress-fill" style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  )
}

function GenusTile({ genus, species_observed, checklist_total, obs_count, last_seen }) {
  const navigate = useNavigate()
  const pct = checklist_total > 0
    ? Math.round((species_observed / checklist_total) * 100)
    : null

  return (
    <div className="tile" onClick={() => navigate(`/genus/${encodeURIComponent(genus)}`)}>
      <div className="tile-body">
        <div className="tile-name">{genus}</div>
        <div className="tile-meta">
          {species_observed}{checklist_total > 0 ? ` of ${checklist_total}` : ''} species
          {obs_count > 0 && ` · ${obs_count} obs`}
        </div>
        {pct !== null && (
          <div className="mini-track" style={{ marginTop: 8 }}>
            <div className="mini-fill" style={{ width: `${pct}%` }} />
          </div>
        )}
        {last_seen && (
          <div className="tile-meta" style={{ marginTop: 4 }}>Last seen {last_seen}</div>
        )}
      </div>
    </div>
  )
}

export default function Home() {
  const { data, loading, error } = useData()
  const navigate = useNavigate()

  if (loading) return <><Nav /><div className="page loading">Loading your museum…</div></>
  if (error)   return <><Nav /><div className="page error">Error: {error}<br/>Run <code>python sync.py</code> first.</div></>

  const { progress, genera, observations } = data
  const pct = progress.pct_complete ?? Math.round(
    (progress.species_observed / Math.max(progress.checklist_total, 1)) * 100
  )

  // Most recently observed specimen for hero photo
  const recentWithPhoto = observations.find(o => o.photos?.length > 0)
  const heroPhoto = recentWithPhoto?.photos[0]?.medium

  return (
    <>
      <Nav />
      <div className="page">

        {/* Header + hero */}
        <div style={{ display: 'grid', gridTemplateColumns: heroPhoto ? '1fr auto' : '1fr', gap: '2rem', alignItems: 'start', marginBottom: '1.5rem' }}>
          <div>
            <h1 style={{ fontSize: '2rem', marginBottom: '0.3rem' }}>Cactus checklist</h1>
            <p style={{ color: 'var(--muted)', fontSize: '0.9rem', fontFamily: 'sans-serif', marginBottom: '1.4rem' }}>
              A personal record of every species seen in the US Southwest. The goal is to see them all<br />
              Synced from iNaturalist · {data.synced_at?.slice(0, 10)}
            </p>

            <div className="progress-label">
              <span>
                <em>{progress.checklist_matched ?? progress.species_observed}</em> of{' '}
                <em>{progress.checklist_total}</em> Desert Southwest species
              </span>
              <strong>{pct}%</strong>
            </div>
            <ProgressBar pct={pct} />
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)', fontFamily: 'sans-serif', marginTop: '0.4rem' }}>
              167-species checklist · Notes from the Road / Erik Gauger
            </div>
          </div>

          {heroPhoto && (
            <img
              src={heroPhoto}
              alt="Most recent specimen"
              style={{ width: 200, height: 160, objectFit: 'cover', borderRadius: 'var(--radius)', border: '1px solid var(--sand-border)' }}
            />
          )}
        </div>

        {/* Stats strip */}
        <div className="stats">
          <div className="stat">
            <div className="stat-num">{progress.total_observations}</div>
            <div className="stat-label">Observations</div>
          </div>
          <div className="stat">
            <div className="stat-num">{progress.checklist_matched ?? progress.species_observed}</div>
            <div className="stat-label">Species seen</div>
          </div>
          <div className="stat">
            <div className="stat-num">{progress.checklist_total - (progress.checklist_matched ?? 0)}</div>
            <div className="stat-label">Remaining</div>
          </div>
          <div className="stat">
            <div className="stat-num">{progress.field_days}</div>
            <div className="stat-label">Field days</div>
          </div>
          <div className="stat">
            <div className="stat-num">{progress.states_visited}</div>
            <div className="stat-label">States</div>
          </div>
          <div className="stat">
            <div className="stat-num">{progress.research_grade}</div>
            <div className="stat-label">Research grade</div>
          </div>
        </div>

        {/* Genus tiles */}
        <div className="section-head">
          <h2>Genera</h2>
          <span className="section-count">{genera.length} genera · alphabetical</span>
        </div>
        <div className="tile-grid">
          {genera.map(g => <GenusTile key={g.genus} {...g} />)}
        </div>

      </div>
    </>
  )
}
