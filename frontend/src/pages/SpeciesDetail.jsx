import { useParams, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Polygon } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import Nav from '../components/Nav'
import { useTaxon, useObservationsForTaxon, useRange } from '../lib/data'

function PhotoGallery({ observations }) {
  const allPhotos = observations.flatMap(o =>
    (o.photos || []).map(p => ({ ...p, obs: o }))
  )
  const [idx, setIdx] = useState(0)

  if (!allPhotos.length) return (
    <div style={{ height: 280, background: 'var(--sand-dark)', borderRadius: 'var(--radius)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontFamily: 'sans-serif' }}>
      No photos
    </div>
  )

  const current = allPhotos[idx]
  return (
    <div>
      <img
        src={current.large || current.medium}
        alt=""
        style={{ width: '100%', height: 300, objectFit: 'cover', borderRadius: 'var(--radius)', display: 'block', marginBottom: 8 }}
      />
      {allPhotos.length > 1 && (
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          {allPhotos.map((p, i) => (
            <img
              key={p.id ?? i}
              src={p.square}
              alt=""
              onClick={() => setIdx(i)}
              style={{
                width: 52, height: 52, objectFit: 'cover', borderRadius: 5, cursor: 'pointer',
                border: i === idx ? '2px solid var(--green)' : '2px solid transparent',
                opacity: i === idx ? 1 : 0.75,
              }}
            />
          ))}
        </div>
      )}
      {current.obs?.inat_url && (
        <div style={{ marginTop: 6 }}>
          <a href={current.obs.inat_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.78rem' }}>
            View on iNaturalist ↗
          </a>
          {current.attribution && (
            <span style={{ fontSize: '0.72rem', color: 'var(--muted)', marginLeft: 8 }}>{current.attribution}</span>
          )}
        </div>
      )}
    </div>
  )
}

function ObsRow({ obs }) {
  const badgeClass = `badge badge-${obs.quality_grade || 'casual'}`
  return (
    <div style={{ display: 'flex', gap: '0.8rem', padding: '0.8rem 0', borderBottom: '1px solid var(--sand-border)', flexWrap: 'wrap' }}>
      {obs.photos?.[0]?.small && (
        <img src={obs.photos[0].small} alt="" style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 6, flexShrink: 0 }} />
      )}
      <div style={{ flex: 1, minWidth: 160 }}>
        <div style={{ fontFamily: 'sans-serif', fontSize: '0.88rem', fontWeight: 500 }}>{obs.observed_on}</div>
        <div style={{ fontFamily: 'sans-serif', fontSize: '0.8rem', color: 'var(--muted)', marginTop: 2 }}>
          {obs.place_guess || (obs.latitude ? `${obs.latitude.toFixed(4)}, ${obs.longitude.toFixed(4)}` : 'No location')}
        </div>
        {obs.description && (
          <div style={{ fontFamily: 'sans-serif', fontSize: '0.8rem', marginTop: 4, color: 'var(--text)' }}>{obs.description}</div>
        )}
        <div style={{ marginTop: 5, display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <span className={badgeClass}>{obs.quality_grade}</span>
          {obs.comments_count > 0 && <span style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>{obs.comments_count} comment{obs.comments_count !== 1 ? 's' : ''}</span>}
          {obs.inat_url && <a href={obs.inat_url} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem' }}>iNaturalist ↗</a>}
        </div>
      </div>
    </div>
  )
}

export default function SpeciesDetail() {
  const { taxonId } = useParams()
  const navigate    = useNavigate()
  const taxon       = useTaxon(taxonId)
  const observations = useObservationsForTaxon(taxonId)
  const range       = useRange(taxonId)

  if (!taxon) return <><Nav /><div className="page loading">Loading…</div></>

  const withCoords = observations.filter(o => o.latitude && o.longitude)
  // Range arrives as one or more rings of [lng, lat]; Leaflet wants [lat, lng]
  const rangeRings = (range?.polygons || (range?.polygon ? [range.polygon] : null))
    ?.map(ring => ring.map(([lng, lat]) => [lat, lng])) ?? null
  const center     = withCoords.length
    ? [withCoords[0].latitude, withCoords[0].longitude]
    : range
      ? [range.centroid[1], range.centroid[0]]
      : [33.5, -112.0]
  const showMap    = withCoords.length > 0 || rangeRings

  return (
    <>
      <Nav />
      <div className="page">
        <div className="back-btn">
          <button className="btn btn-secondary btn-small" onClick={() => navigate(-1)}>← Back</button>
        </div>

        <h1 style={{ fontSize: '1.9rem', fontStyle: 'italic', marginBottom: '0.2rem' }}>{taxon.name}</h1>
        {taxon.common_name && (
          <div style={{ color: 'var(--muted)', fontFamily: 'sans-serif', marginBottom: '1.5rem' }}>{taxon.common_name}</div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
          {/* Photos */}
          <div>
            <div className="section-head" style={{ marginTop: 0 }}>
              <h2>Photos</h2>
              <span className="section-count">{observations.reduce((n, o) => n + (o.photos?.length || 0), 0)} total</span>
            </div>
            <div style={{ marginTop: '0.8rem' }}>
              <PhotoGallery observations={observations} />
            </div>
          </div>

          {/* Map */}
          <div>
            <div className="section-head" style={{ marginTop: 0 }}>
              <h2>Where seen</h2>
              <span className="section-count">
                {withCoords.length} with GPS
                {range && ` · range from ${range.kept_points} sightings`}
              </span>
            </div>
            <div style={{ marginTop: '0.8rem' }}>
              {showMap ? (
                <MapContainer center={center} zoom={withCoords.length ? 7 : 6} className="map-wrap">
                  <TileLayer
                    attribution='© <a href="https://openstreetmap.org">OpenStreetMap</a> · range from <a href="https://inaturalist.org">iNaturalist</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {rangeRings && rangeRings.map((ring, i) => (
                    <Polygon
                      key={i}
                      positions={ring}
                      pathOptions={{ color: '#3a7d44', weight: 1.5, fillColor: '#3a7d44', fillOpacity: 0.15 }}
                    >
                      <Popup>
                        <strong>Native range</strong><br />
                        {range.kept_points} community sightings
                        {range.outliers_removed > 0 && ` (${range.outliers_removed} outliers removed)`}
                      </Popup>
                    </Polygon>
                  ))}
                  {withCoords.map(o => (
                    <CircleMarker
                      key={o.id}
                      center={[o.latitude, o.longitude]}
                      radius={7}
                      pathOptions={{ color: '#1f4d27', fillColor: '#3a7d44', fillOpacity: 0.9, weight: 1.5 }}
                    >
                      <Popup>
                        <strong>{o.observed_on}</strong><br />
                        {o.place_guess}<br />
                        <span className={`badge badge-${o.quality_grade}`}>{o.quality_grade}</span>
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
              ) : (
                <div style={{ height: 240, background: 'var(--sand-dark)', borderRadius: 'var(--radius)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.85rem' }}>
                  No GPS coordinates recorded
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Taxonomy strip */}
        <div style={{ background: 'var(--white)', border: '1px solid var(--sand-border)', borderRadius: 'var(--radius)', padding: '0.8rem 1.2rem', display: 'flex', gap: '2rem', flexWrap: 'wrap', fontFamily: 'sans-serif', fontSize: '0.83rem' }}>
          <div><span style={{ color: 'var(--muted)' }}>Family </span>Cactaceae</div>
          <div><span style={{ color: 'var(--muted)' }}>Genus </span><em>{taxon.genus}</em></div>
          <div><span style={{ color: 'var(--muted)' }}>Species </span><em>{taxon.name}</em></div>
          <div><span style={{ color: 'var(--muted)' }}>Rank </span>{taxon.rank}</div>
          {taxon.inat_url && (
            <a href={taxon.inat_url} target="_blank" rel="noreferrer">iNaturalist page ↗</a>
          )}
        </div>

        {/* Observation list */}
        <div className="section-head">
          <h2>All observations</h2>
          <span className="section-count">{observations.length} records</span>
        </div>
        {observations
          .slice()
          .sort((a, b) => (b.observed_on || '').localeCompare(a.observed_on || ''))
          .map(o => <ObsRow key={o.id} obs={o} />)
        }

      </div>
    </>
  )
}
