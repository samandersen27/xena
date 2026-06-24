// AddObservation — placeholder pointing to iNaturalist
// Since we're using iNat as the source of truth, the best
// workflow is to add the observation there, then re-run sync.py

import { useNavigate } from 'react-router-dom'
import Nav from '../components/Nav'
import RichnessMap from '../components/RichnessMap'

export function AddObservation() {
  const navigate = useNavigate()
  return (
    <>
      <Nav />
      <div className="page" style={{ maxWidth: 600 }}>
        <div className="back-btn">
          <button className="btn btn-secondary btn-small" onClick={() => navigate(-1)}>← Back</button>
        </div>
        <h1 style={{ marginBottom: '0.5rem' }}>Add an observation</h1>
        <p style={{ color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
          Since Xena syncs from iNaturalist, the best way to add a new sighting is directly on iNaturalist — then run <code>python sync.py</code> to pull it in.
        </p>
        <a
          href="https://www.inaturalist.org/observations/new"
          target="_blank"
          rel="noreferrer"
          className="btn btn-primary"
          style={{ display: 'inline-block', marginBottom: '1.5rem' }}
        >
          Add on iNaturalist ↗
        </a>
        <p style={{ fontFamily: 'sans-serif', fontSize: '0.83rem', color: 'var(--muted)' }}>
          After logging it there, come back and run:<br />
          <code style={{ background: 'var(--sand-dark)', padding: '2px 6px', borderRadius: 4 }}>python sync.py</code><br />
          then rebuild the site with:<br />
          <code style={{ background: 'var(--sand-dark)', padding: '2px 6px', borderRadius: 4 }}>npm run build</code>
        </p>
      </div>
    </>
  )
}

export function Curiosity() {
  return (
    <>
      <Nav />
      <div className="page">
        <h1 style={{ marginBottom: '0.5rem' }}>Curiosity layer</h1>
        <p style={{ color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
          Home for special studies — saguaro bifurcation, opuntia pad characterization, and whatever else seems interesting along the way.
        </p>

        {/* Species richness contour map */}
        <div className="section-head" style={{ marginTop: 0 }}>
          <h2>Species richness</h2>
          <span className="section-count">overlapping native ranges · SW states</span>
        </div>
        <p style={{ color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.83rem', marginBottom: '0.9rem' }}>
          How many native cactus ranges overlap each spot, counted from the iNaturalist range polygons. Warmer = more species share that ground.
        </p>
        <RichnessMap label="Native species overlapping:" />

        {/* Splitter's Opuntia diversity */}
        <div className="section-head">
          <h2>Splitter's Opuntia diversity</h2>
          <span className="section-count">Opuntia Web species also on iNaturalist</span>
        </div>
        <p style={{ color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.83rem', marginBottom: '0.9rem' }}>
          The same overlap count, but restricted to prickly-pears recognized by <a href="https://www.opuntiads.com/" target="_blank" rel="noreferrer">Opuntia Web</a> that iNaturalist also treats as valid species — a finely-split view of where <em>Opuntia</em> diversity concentrates.
        </p>
        <RichnessMap src="/xena/opuntia_richness.json" label="Opuntia species overlapping:" />

        <div className="section-head">
          <h2>Studies</h2>
        </div>
        <div className="tile-grid">
          {[
            { title: 'Saguaro bifurcation', desc: 'Record and map crested saguaros across the Sonoran Desert.' },
            { title: 'Opuntia pad characterization', desc: 'Systematic pad measurements to distinguish range-overlapping prickly pears.' },
            { title: 'More to come…', desc: 'New study types can be added any time.' },
          ].map(s => (
            <div key={s.title} className="tile" style={{ cursor: 'default' }}>
              <div className="tile-body">
                <div className="tile-name" style={{ fontStyle: 'normal', fontWeight: 500 }}>{s.title}</div>
                <div className="tile-meta" style={{ marginTop: 6 }}>{s.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
