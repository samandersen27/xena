import Nav from '../components/Nav'

const FIGS = [
  {
    id: 'hybrid',
    src: '/xena/figures/fig_hybrid.png',
    title: 'The coastal Opuntia hybrid complex',
    finding: '70% of hybrid records fall within the O. littoralis – O. oricola zone of sympatry — the hybrids track where the parents meet.',
    methods: 'Concave-hull ranges (Grubbs-filtered) of three parental taxa; hybrid occurrences and a kernel-density "hybridization hotspot" surface. n = 2,684 research-grade observations.',
  },
  {
    id: 'phenology',
    src: '/xena/figures/fig_phenology.png',
    title: 'Flowering phenology from photo annotations',
    finding: 'Complex-wide flowering peaks in late spring (May–June), with taxon-level offsets that could reinforce or break down reproductive isolation.',
    methods: 'iNaturalist "Plant Phenology = Flowering" photo annotations, binned by month-of-year (per-taxon where n ≥ 25, otherwise observation activity as a proxy).',
  },
  {
    id: 'effort',
    src: '/xena/figures/fig_effort.png',
    title: 'Effort-corrected relative occurrence',
    finding: 'Mapping the fraction of all prickly-pear records that are the coastal complex corrects for where people look — not just where they go — revealing the true coastal signal.',
    methods: 'Target-group background: each cell = focal records ÷ all-Opuntia records (cells with ≥ 4 background observations). Background n = 9,000.',
  },
  {
    id: 'niche',
    src: '/xena/figures/fig_niche.png',
    title: 'Environmental niche divergence',
    finding: 'Parents and hybrids separate along the two dominant coastal gradients — distance-to-coast (marine/fog influence) and elevation — with Schoener’s D quantifying pairwise overlap.',
    methods: 'Elevation from the Open-Meteo DEM; distance-to-coast from the Natural Earth shoreline. 1-SD ellipses; Schoener’s D from a 2-D occupancy grid.',
  },
]

const STRENGTHEN = [
  ['Verify hybrid IDs', 'Hybrids are under- and mis-identified on iNaturalist. Treat hybrid layers as “minimum known”, restrict to community-ID agreement, and add an ID-confidence sensitivity panel.'],
  ['Add true bioclim', 'Swap the 2-axis coastal niche for WorldClim/PRISM bioclimatic variables (temperature seasonality, summer fog, precipitation) and compute niche overlap with ENMTools.'],
  ['Species distribution models', 'MaxEnt per taxon → predicted suitable habitat; parent-overlap = predicted hybrid zones; project to 2070 climate to forecast hybrid-zone movement.'],
  ['Cline analysis', 'Fit a hybrid-index cline along a coast-to-inland transect (HZAR) to characterize the tension zone — and motivate a genomics follow-up.'],
  ['Conservation overlay', 'Intersect ranges with protected areas (CPAD/GAP) and the urban footprint to flag unprotected, urban-adjacent coastal cactus scrub (cactus-wren habitat).'],
  ['Cartographic polish', 'Projected CRS (California Albers), hillshade relief, county and protected-area lines, locator inset, and bootstrapped range uncertainty.'],
]

export default function ProposalFigures() {
  return (
    <>
      <Nav />
      <div className="page" style={{ maxWidth: 1000 }}>
        <h1 style={{ marginBottom: '0.4rem' }}>Proposal figures</h1>
        <p style={{ color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.9rem', lineHeight: 1.6, marginBottom: '0.4rem' }}>
          Research-grade graphics for the coastal Southern California <em>Opuntia</em> hybrid complex, built entirely
          from iNaturalist research-grade observations. Each figure is a standalone, citable panel for a grant or
          manuscript. Click any figure to open it full-size for download.
        </p>
        <p style={{ color: 'var(--muted)', fontFamily: 'sans-serif', fontSize: '0.78rem', marginBottom: '2rem' }}>
          Data: iNaturalist (research-grade, Grubbs-filtered) · elevation: Open-Meteo · shoreline: Natural Earth.
        </p>

        {FIGS.map(f => (
          <section key={f.id} style={{ marginBottom: '2.6rem' }}>
            <div className="section-head" style={{ marginTop: 0 }}>
              <h2>{f.title}</h2>
              <a href={f.src} target="_blank" rel="noreferrer" className="section-count">open / download ↗</a>
            </div>
            <a href={f.src} target="_blank" rel="noreferrer">
              <img src={f.src} alt={f.title}
                style={{ width: '100%', borderRadius: 'var(--radius)', border: '1px solid var(--sand-border)', background: '#fff', display: 'block' }} />
            </a>
            <p style={{ fontFamily: 'sans-serif', fontSize: '0.9rem', color: 'var(--text)', margin: '0.7rem 0 0.3rem', fontWeight: 500 }}>
              {f.finding}
            </p>
            <p style={{ fontFamily: 'sans-serif', fontSize: '0.78rem', color: 'var(--muted)', lineHeight: 1.55 }}>
              <strong>Methods.</strong> {f.methods}
            </p>
          </section>
        ))}

        <div className="section-head"><h2>Strengthening these analyses</h2></div>
        <div className="tile-grid">
          {STRENGTHEN.map(([t, d]) => (
            <div key={t} className="tile" style={{ cursor: 'default' }}>
              <div className="tile-body">
                <div className="tile-name" style={{ fontStyle: 'normal', fontWeight: 600 }}>{t}</div>
                <div className="tile-meta" style={{ marginTop: 6, lineHeight: 1.5 }}>{d}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
