import { useEffect, useState, useMemo } from 'react'
import { MapContainer, TileLayer, ImageOverlay, Polyline } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useSwStates } from '../lib/data'

// Banded (contour-style) colormap for species richness
const BANDS = [
  { min: 1,  max: 4,   rgb: [255, 255, 178], label: '1–4' },
  { min: 5,  max: 9,   rgb: [254, 217, 118], label: '5–9' },
  { min: 10, max: 14,  rgb: [254, 178, 76],  label: '10–14' },
  { min: 15, max: 20,  rgb: [253, 141, 60],  label: '15–20' },
  { min: 21, max: 28,  rgb: [252, 78, 42],   label: '21–28' },
  { min: 29, max: 38,  rgb: [227, 26, 28],   label: '29–38' },
  { min: 39, max: 999, rgb: [177, 0, 38],    label: '39+' },
]
const ALPHA = 175

function colorFor(v) {
  if (v == null || v < 1) return [0, 0, 0, 0]   // outside SW or no species
  for (const b of BANDS) if (v >= b.min && v <= b.max) return [...b.rgb, ALPHA]
  return [...BANDS[BANDS.length - 1].rgb, ALPHA]
}

export default function RichnessMap() {
  const [grid, setGrid] = useState(null)
  const states = useSwStates()

  useEffect(() => {
    fetch('/xena/richness.json').then(r => r.json()).then(setGrid).catch(() => {})
  }, [])

  // Paint the grid to a canvas and hand Leaflet a data-URL image overlay
  const url = useMemo(() => {
    if (!grid) return null
    const { nx, ny, data } = grid
    const cv = document.createElement('canvas')
    cv.width = nx; cv.height = ny
    const ctx = cv.getContext('2d')
    const img = ctx.createImageData(nx, ny)
    for (let row = 0; row < ny; row++) {
      const src = data[ny - 1 - row]      // data rows go south->north; canvas top = north
      for (let x = 0; x < nx; x++) {
        const [r, g, b, a] = colorFor(src[x])
        const i = (row * nx + x) * 4
        img.data[i] = r; img.data[i + 1] = g; img.data[i + 2] = b; img.data[i + 3] = a
      }
    }
    ctx.putImageData(img, 0, 0)
    return cv.toDataURL()
  }, [grid])

  if (!grid || !url) {
    return <div style={{ height: 480, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontFamily: 'sans-serif' }}>Building richness map…</div>
  }

  const [W, S, E, N] = grid.bbox
  const bounds = [[S, W], [N, E]]

  return (
    <div>
      <div style={{ height: 480, borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--sand-border)' }}>
        <MapContainer bounds={bounds} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
          <TileLayer
            attribution='© <a href="https://openstreetmap.org">OpenStreetMap</a> · richness from <a href="https://inaturalist.org">iNaturalist</a> ranges'
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

      {/* Legend */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10, marginTop: 10, fontFamily: 'sans-serif', fontSize: '0.74rem', color: 'var(--muted)' }}>
        <span style={{ fontWeight: 600, color: 'var(--text)' }}>Native species overlapping:</span>
        {BANDS.map(b => (
          <span key={b.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 16, height: 12, borderRadius: 2, background: `rgb(${b.rgb.join(',')})`, display: 'inline-block', border: '1px solid rgba(0,0,0,0.15)' }} />
            {b.label}
          </span>
        ))}
        <span style={{ marginLeft: 'auto', color: 'var(--text)' }}>peak: <strong>{grid.max}</strong> species</span>
      </div>
    </div>
  )
}
