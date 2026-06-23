// Lightweight static SVG thumbnail of a species' iNaturalist range polygon,
// drawn over a faint Desert-Southwest states outline. No Leaflet — cheap enough
// to render on every tile.

const W = 160, H = 92
// Fixed equirectangular window over the US Southwest
const L = -125, R = -93, T = 43, B = 25

function project([lng, lat]) {
  return [
    ((lng - L) / (R - L)) * W,
    ((T - lat) / (T - B)) * H,
  ]
}

const toPts = ring => ring.map(project).map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')

export default function RangeThumb({ range, states = [], height = 92 }) {
  return (
    <svg
      className="range-thumb"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ height }}
      role="img"
      aria-label={range ? 'Native range' : 'No range data'}
    >
      <rect x="0" y="0" width={W} height={H} className="rt-bg" />
      {states.flatMap((s, i) =>
        (s.rings || (s.ring ? [s.ring] : [])).map((ring, j) => (
          <polygon key={`${i}-${j}`} points={toPts(ring)} className="rt-state" />
        ))
      )}
      {range?.polygon
        ? <polygon points={toPts(range.polygon)} className="rt-range" />
        : <text x={W / 2} y={H / 2} className="rt-none" textAnchor="middle">no range data</text>
      }
    </svg>
  )
}
