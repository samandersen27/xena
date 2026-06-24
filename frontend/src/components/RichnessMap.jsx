import { useEffect, useState, useMemo } from 'react'
import { MapContainer, TileLayer, ImageOverlay, Polyline } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useSwStates } from '../lib/data'

// YlOrRd ramp; bands are derived from each map's peak so low-richness
// layers (e.g. Opuntia-only) still use the full color range.
const RAMP = [
  [255, 255, 178], [254, 217, 118], [254, 178, 76], [253, 141, 60],
  [252, 78, 42], [227, 26, 28], [177, 0, 38],
]
const ALPHA = 175

function buildBands(max) {
  if (!max || max < 1) return []
  const n = Math.min(7, max)
  const bands = []
  for (let k = 0; k < n; k++) {
    const lo = Math.round(1 + (max - 1) * k / n)
    const hiRaw = k === n - 1 ? max : Math.round(1 + (max - 1) * (k + 1) / n) - 1
    const hi = Math.max(lo, hiRaw)
    const ci = n === 1 ? RAMP.length - 1 : Math.round(k * (RAMP.length - 1) / (n - 1))
    bands.push({ min: lo, max: hi, rgb: RAMP[ci], label: lo === hi ? `${lo}` : `${lo}–${hi}` })
  }
  return bands
}

export default function RichnessMap({ src = '/xena/richness.json', label = 'Native species overlapping:' }) {
  const [grid, setGrid] = useState(null)
  const states = useSwStates()

  useEffect(() => {
    let alive = true
    setGrid(null)
    fetch(src).then(r => r.json()).then(g => { if (alive) setGrid(g) }).catch(() => {})
    return () => { alive = false }
  }, [src])

  const bands = useMemo(() => (grid ? buildBands(grid.max) : []), [grid])

  const colorFor = useMemo(() => {
    return v => {
      if (v == null || v < 1) return [0, 0, 0, 0]
      for (const b of bands) if (v >= b.min && v <= b.max) return [...b.rgb, ALPHA]
      return bands.length ? [...bands[bands.length - 1].rgb, ALPHA] : [0, 0, 0, 0]
    }
  }, [bands])

  // Paint to a canvas, resampling rows into Web Mercator-Y so the overlay
  // aligns with Leaflet's projection (longitude is already linear).
  const url = useMemo(() => {
    if (!grid || !bands.length) return null
    const { nx, ny, data, bbox } = grid
    const [, S, , N] = bbox
    const D2R = Math.PI / 180, R2D = 180 / Math.PI
    const mercY = lat => Math.log(Math.tan(Math.PI / 4 + (lat * D2R) / 2))
    const invMercY = y => (2 * Math.atan(Math.exp(y)) - Math.PI / 2) * R2D
    const yN = mercY(N), yS = mercY(S)
    const H = ny * 2
    const cv = document.createElement('canvas')
    cv.width = nx; cv.height = H
    const ctx = cv.getContext('2d')
    const img = ctx.createImageData(nx, H)
    for (let row = 0; row < H; row++) {
      const my = yN - (row / (H - 1)) * (yN - yS)
      const lat = invMercY(my)
      let j = Math.round((lat - S) / grid.res)
      if (j < 0) j = 0; else if (j > ny - 1) j = ny - 1
      const srcRow = data[j]
      for (let x = 0; x < nx; x++) {
        const [r, g, b, a] = colorFor(srcRow[x])
        const i = (row * nx + x) * 4
        img.data[i] = r; img.data[i + 1] = g; img.data[i + 2] = b; img.data[i + 3] = a
      }
    }
    ctx.putImageData(img, 0, 0)
    return cv.toDataURL()
  }, [grid, bands, colorFor])

  if (!grid || !url) {
    return <div style={{ height: 480, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontFamily: 'sans-serif' }}>Building map…</div>
  }

  const [W, S, E, N] = grid.bbox
  const bounds = [[S, W], [N, E]]

  return (
    <div>
      <div style={{ height: 480, borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--sand-border)' }}>
        <MapContainer bounds={bounds} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
          <TileLayer
            attribution='© <a href="https://openstreetmap.org">OpenStreetMap</a> · ranges from <a href="https://inaturalist.org">iNaturalist</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ImageOverlay url={url} bounds={bounds} opacity={0.72} />
          {states.flatMap((st, i) =>
            (st.rings || []).map((ring, j) => (
              <Polyline key={`${i}-${j}`} positions={ring.map(([lo, la]) => [la, lo])}
                pathOptions={{ color: '#5a4a32', weight: 1, opacity: 0.5, fill: false }} />
            ))
          )}
        </MapContainer>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10, marginTop: 10, fontFamily: 'sans-serif', fontSize: '0.74rem', color: 'var(--muted)' }}>
        <span style={{ fontWeight: 600, color: 'var(--text)' }}>{label}</span>
        {bands.map(b => (
          <span key={b.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 16, height: 12, borderRadius: 2, background: `rgb(${b.rgb.join(',')})`, display: 'inline-block', border: '1px solid rgba(0,0,0,0.15)' }} />
            {b.label}
          </span>
        ))}
        <span style={{ marginLeft: 'auto', color: 'var(--text)' }}>peak: <strong>{grid.max}</strong></span>
      </div>
    </div>
  )
}
