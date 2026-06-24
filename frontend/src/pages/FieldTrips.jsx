import { useState, useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, Polyline, Polygon, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import Nav from '../components/Nav'
import { useData, useRanges } from '../lib/data'

const NOMINATIM = 'https://nominatim.openstreetmap.org/search'
const VALHALLA  = 'https://valhalla1.openstreetmap.de/route'
const CORRIDOR_KM = 25
const KM_PER_DEG = 111

// ── Geometry: does the route pass through (or near) a range polygon? ────────────
function pointInRing(pt, ring) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1]
    if (((yi > pt[1]) !== (yj > pt[1])) &&
        (pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi)) inside = !inside
  }
  return inside
}
const ccw = (a, b, c) => (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
const segCross = (a, b, c, d) => ccw(a, c, d) !== ccw(b, c, d) && ccw(a, b, c) !== ccw(a, b, d)
function segCrossesRing(a, b, ring) {
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++)
    if (segCross(a, b, ring[j], ring[i])) return true
  return false
}
function distPointToSegKm(p, a, b) {
  const vx = b[0] - a[0], vy = b[1] - a[1]
  const wx = p[0] - a[0], wy = p[1] - a[1]
  const len2 = vx * vx + vy * vy
  let t = len2 ? (wx * vx + wy * vy) / len2 : 0
  t = Math.max(0, Math.min(1, t))
  const dx = p[0] - (a[0] + t * vx), dy = p[1] - (a[1] + t * vy)
  const cosLat = Math.cos(p[1] * Math.PI / 180)
  return Math.sqrt((dx * cosLat) ** 2 + dy ** 2) * KM_PER_DEG
}
function routeHitsRange(route, range, tolKm) {
  const ring = range.polygon
  const [minX, minY, maxX, maxY] = range.bbox
  const pad = tolKm / KM_PER_DEG + 0.01
  let rMinX = Infinity, rMinY = Infinity, rMaxX = -Infinity, rMaxY = -Infinity
  for (const p of route) {
    if (p[0] < rMinX) rMinX = p[0]; if (p[0] > rMaxX) rMaxX = p[0]
    if (p[1] < rMinY) rMinY = p[1]; if (p[1] > rMaxY) rMaxY = p[1]
  }
  if (rMaxX < minX - pad || rMinX > maxX + pad || rMaxY < minY - pad || rMinY > maxY + pad) return null
  for (let i = 0; i < route.length; i++) {
    if (pointInRing(route[i], ring)) return route[i]
    if (i > 0 && segCrossesRing(route[i - 1], route[i], ring)) return route[i]
  }
  if (tolKm > 0) {
    for (const v of ring)
      for (let i = 1; i < route.length; i++)
        if (distPointToSegKm(v, route[i - 1], route[i]) <= tolKm) return v
  }
  return null
}

// ── Routing helpers ─────────────────────────────────────────────────────────────
async function geocode(q) {
  const url = `${NOMINATIM}?q=${encodeURIComponent(q)}&format=json&limit=1`
  const data = await (await fetch(url, { headers: { Accept: 'application/json' } })).json()
  if (!data.length) throw new Error(`Couldn't find "${q}"`)
  return { lat: +data[0].lat, lng: +data[0].lon, name: data[0].display_name.split(',').slice(0, 2).join(',').trim() }
}
function decodePolyline6(str) {
  const out = []; let i = 0, lat = 0, lng = 0
  while (i < str.length) {
    let b, shift = 0, result = 0
    do { b = str.charCodeAt(i++) - 63; result |= (b & 0x1f) << shift; shift += 5 } while (b >= 0x20)
    lat += (result & 1) ? ~(result >> 1) : (result >> 1)
    shift = 0; result = 0
    do { b = str.charCodeAt(i++) - 63; result |= (b & 0x1f) << shift; shift += 5 } while (b >= 0x20)
    lng += (result & 1) ? ~(result >> 1) : (result >> 1)
    out.push([lng / 1e6, lat / 1e6])
  }
  return out
}
async function getRoute(from, to) {
  const body = { locations: [{ lon: from.lng, lat: from.lat }, { lon: to.lng, lat: to.lat }], costing: 'auto' }
  const res = await fetch(VALHALLA, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.error || 'No drivable route found.') }
  const trip = (await res.json()).trip
  const leg = trip.legs[0]
  const coords = typeof leg.shape === 'string' ? decodePolyline6(leg.shape) : leg.shape.coordinates
  return { coords, distanceKm: trip.summary.length, durationMin: trip.summary.time / 60 }
}

function numIcon(n) {
  return L.divIcon({
    className: '',
    html: `<div style="width:26px;height:26px;border-radius:50%;background:#c2772f;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;font-family:sans-serif;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.4)">${n}</div>`,
    iconSize: [26, 26], iconAnchor: [13, 13], popupAnchor: [0, -14],
  })
}

function FitBounds({ coords }) {
  const map = useMap()
  useEffect(() => {
    if (coords && coords.length) {
      map.fitBounds(coords.map(([lo, la]) => [la, lo]), { padding: [30, 30] })
    }
  }, [coords, map])
  return null
}

export default function FieldTrips() {
  const { data, loading } = useData()
  const { byId } = useRanges()

  const [cityA, setCityA] = useState('')
  const [cityB, setCityB] = useState('')
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState('')
  const [result, setResult] = useState(null)   // { from, to, route, hits }
  const [map, setMap] = useState(null)

  // Sam's observed taxa (exclude from suggestions)
  const samSeen = useMemo(
    () => new Set((data?.taxa || []).filter(t => (t.obs_count || 0) > 0 && t.inat_id).map(t => t.inat_id)),
    [data]
  )
  const rangeEntries = useMemo(() => Object.entries(byId || {}), [byId])
  // Common names live in the checklist, not in ranges.json — index by iNat id and name
  const commonName = useMemo(() => {
    const byId = {}, byName = {}
    ;(data?.checklist || []).forEach(c => {
      if (c.inat_id) byId[c.inat_id] = c.common_name
      if (c.name) byName[c.name.toLowerCase()] = c.common_name
    })
    return (id, name) => byId[id] || byName[(name || '').toLowerCase()] || ''
  }, [data])

  async function run() {
    if (running) return
    if (!cityA.trim() || !cityB.trim()) { setStatus('Enter both a start and end city.'); return }
    if (!rangeEntries.length) { setStatus('Range data not loaded yet.'); return }
    setRunning(true); setResult(null)
    try {
      setStatus('Geocoding cities…')
      const [from, to] = await Promise.all([geocode(cityA), geocode(cityB)])
      setStatus('Finding driving route…')
      const route = await getRoute(from, to)
      setStatus(`Testing route against ${rangeEntries.length} native ranges…`)
      const hits = []
      for (const [id, range] of rangeEntries) {
        if (samSeen.has(Number(id))) continue
        const at = routeHitsRange(route.coords, range, CORRIDOR_KM)
        if (at) hits.push({ id, range, at })
      }
      hits.sort((p, q) => p.at[0] - q.at[0])
      setResult({ from, to, route, hits })
      const mi = Math.round(route.distanceKm * 0.621)
      const h = Math.floor(route.durationMin / 60), m = Math.round(route.durationMin % 60)
      setStatus(`${mi} mi · ~${h}h ${m}m · ${hits.length} native cact${hits.length === 1 ? 'us' : 'i'} along the route you haven't logged yet.`)
    } catch (e) {
      setStatus('Error: ' + e.message)
    }
    setRunning(false)
  }

  const onKey = e => { if (e.key === 'Enter') run() }

  return (
    <>
      <Nav />
      <div style={{ display: 'flex', height: 'calc(100vh - 54px)' }}>
        {/* Controls + results */}
        <div style={{ width: 340, flexShrink: 0, borderRight: '1px solid var(--sand-border)', background: 'var(--white)', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '1.1rem 1.2rem', borderBottom: '1px solid var(--sand-border)' }}>
            <h1 style={{ fontSize: '1.3rem', marginBottom: '0.3rem' }}>Field trips</h1>
            <p style={{ color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.8rem', lineHeight: 1.5 }}>
              Plan a drive and see which native cacti you'd pass — only species whose range the route crosses, and that aren't on your list yet.
            </p>
          </div>

          <div style={{ padding: '1.1rem 1.2rem', borderBottom: '1px solid var(--sand-border)', fontFamily: 'sans-serif' }}>
            <label style={{ fontSize: '0.72rem', color: 'var(--muted)', display: 'block', marginBottom: 3 }}>Start city</label>
            <input value={cityA} onChange={e => setCityA(e.target.value)} onKeyDown={onKey}
              placeholder="e.g. Los Angeles, CA" className="ft-input" />
            <label style={{ fontSize: '0.72rem', color: 'var(--muted)', display: 'block', margin: '10px 0 3px' }}>End city</label>
            <input value={cityB} onChange={e => setCityB(e.target.value)} onKeyDown={onKey}
              placeholder="e.g. St. George, UT" className="ft-input" />
            <button className="btn btn-primary" style={{ width: '100%', marginTop: 12 }} onClick={run} disabled={running || loading}>
              {running ? 'Searching…' : 'Find cacti along route →'}
            </button>
            {status && <div style={{ fontSize: '0.76rem', color: 'var(--muted)', marginTop: 10, lineHeight: 1.5 }}>{status}</div>}
          </div>

          {result && (
            <div style={{ flex: 1 }}>
              {result.hits.length === 0
                ? <div style={{ padding: '1.2rem', fontFamily: 'sans-serif', fontSize: '0.83rem', color: 'var(--muted)' }}>
                    The route doesn't pass through any native range that isn't already on your list.
                  </div>
                : result.hits.map((hit, i) => (
                    <div key={hit.id}
                      onClick={() => map && map.panTo([hit.at[1], hit.at[0]], { animate: true })}
                      style={{ display: 'flex', gap: 10, padding: '0.7rem 1.2rem', borderBottom: '1px solid var(--sand-border)', cursor: 'pointer', alignItems: 'flex-start' }}>
                      <div style={{ width: 22, height: 22, borderRadius: '50%', background: '#c2772f', color: '#fff', fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontFamily: 'sans-serif', marginTop: 1 }}>{i + 1}</div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontStyle: 'italic', fontSize: '0.86rem' }}>{hit.range.display_name}</div>
                        <div style={{ fontSize: '0.74rem', color: 'var(--muted)', fontFamily: 'sans-serif' }}>{commonName(hit.id, hit.range.display_name)}</div>
                        <a href={`https://www.inaturalist.org/taxa/${hit.id}`} target="_blank" rel="noreferrer"
                          onClick={e => e.stopPropagation()} style={{ fontSize: '0.72rem' }}>iNaturalist ↗</a>
                      </div>
                    </div>
                  ))
              }
            </div>
          )}
        </div>

        {/* Map */}
        <div style={{ flex: 1 }}>
          <MapContainer center={[36.5, -114]} zoom={6} style={{ height: '100%', width: '100%' }} ref={setMap}>
            <TileLayer
              attribution='© <a href="https://openstreetmap.org">OpenStreetMap</a> · ranges from <a href="https://inaturalist.org">iNaturalist</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {result && (
              <>
                <FitBounds coords={result.route.coords} />
                <Polyline positions={result.route.coords.map(([lo, la]) => [la, lo])}
                  pathOptions={{ color: '#b5402f', weight: 3.5, opacity: 0.8, dashArray: '10,7' }} />
                {result.hits.map(hit => (
                  <Polygon key={'p' + hit.id} positions={hit.range.polygon.map(([lo, la]) => [la, lo])}
                    pathOptions={{ color: '#c2772f', weight: 1.5, fillColor: '#c2772f', fillOpacity: 0.12 }} />
                ))}
                {result.hits.map((hit, i) => (
                  <Marker key={'m' + hit.id} position={[hit.at[1], hit.at[0]]} icon={numIcon(i + 1)}>
                    <Popup>
                      <em style={{ fontSize: 13 }}>{hit.range.display_name}</em><br />
                      <span style={{ fontSize: 11, color: '#888' }}>{commonName(hit.id, hit.range.display_name)}</span><br />
                      <a href={`https://www.inaturalist.org/taxa/${hit.id}`} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>iNaturalist ↗</a>
                    </Popup>
                  </Marker>
                ))}
              </>
            )}
          </MapContainer>
        </div>
      </div>
    </>
  )
}
