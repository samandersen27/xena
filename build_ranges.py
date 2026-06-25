"""
Xena — range polygon builder (with Grubbs outlier rejection)

For EVERY species on the Desert Southwest checklist (not just observed ones):
  1. Resolve the species to its iNaturalist taxon ID
  2. Pull all research-grade community sightings (coordinates)
  3. Reject geographic outliers with an iterative two-sided Grubbs test
  4. Define the native distribution as the convex hull of the surviving points
  5. Store the polygon (+ stats) in frontend/public/data.json under "ranges",
     keyed by iNat taxon ID, and tag each checklist entry with its inat_id.

Run with:  python build_ranges.py
Reads:  frontend/public/data.json   (run sync.py first)
Writes: frontend/public/data.json   (adds/refreshes "ranges")
Caches: coords_cache.json, taxon_ids.json   (delete to force a re-fetch)
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

import numpy as np
from scipy import stats
import shapely
from shapely.geometry import MultiPoint, box, shape
from shapely.ops import unary_union

HERE        = Path(__file__).parent
DATA_PATH   = HERE / "frontend" / "public" / "data.json"
RANGES_PATH = HERE / "frontend" / "public" / "ranges.json"
COORDS_CACHE = HERE / "coords_cache.json"
IDS_CACHE   = HERE / "taxon_ids.json"
HEADERS     = {"User-Agent": "Xena-CactusMuseum/0.2"}
SLEEP       = 1.1
CACTACEAE   = 47903
MIN_POINTS_FOR_HULL  = 3
MIN_POINTS_FOR_GRUBBS = 7      # below this, keep every point (sample too small)
MAX_OBS_PER_SPECIES   = 1200
GRUBBS_ALPHA = 0.05

# Refined-hull recipe: concave hull, then clip to land so over-water "teeth"
# vanish and offshore islands become their own polygons.
CONCAVE_RATIO = 0.30
MIN_RING_AREA = 0.0004          # deg^2 — drop tiny coastline slivers
LAND_CACHE    = HERE / "land_mask.wkt"
LAND_URL      = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson"
NA_BBOX       = (-128.0, 18.0, -80.0, 50.0)   # continental US + N. Mexico margin


def get_land_mask():
    """North-America land polygon (Natural Earth 50m, incl. Channel Islands),
    cached locally. One non-iNat download, then reused."""
    if LAND_CACHE.exists():
        return shapely.from_wkt(LAND_CACHE.read_text(encoding="utf-8"))
    print("  downloading Natural Earth land mask (one-time)…", flush=True)
    data = json.loads(urllib.request.urlopen(
        urllib.request.Request(LAND_URL, headers=HEADERS), timeout=180).read())
    bb = box(*NA_BBOX)
    parts = [shape(f["geometry"]).intersection(bb) for f in data["features"]
             if shape(f["geometry"]).intersects(bb)]
    land = unary_union([p for p in parts if not p.is_empty])
    LAND_CACHE.write_text(land.wkt, encoding="utf-8")
    return land


def refined_polygons(points, land, ratio=CONCAVE_RATIO, minarea=MIN_RING_AREA):
    """Grubbs-filtered points -> concave hull clipped to land -> list of
    exterior rings (largest first). Islands come back as separate rings."""
    mp = MultiPoint([tuple(p) for p in points])
    hull = shapely.concave_hull(mp, ratio=ratio)
    if not hull.is_valid:
        hull = hull.buffer(0)
    clipped = hull.intersection(land) if land is not None else hull
    if clipped.is_empty:
        clipped = hull                      # fully offshore? keep unclipped
    clipped = clipped.simplify(0.002)
    geoms = clipped.geoms if clipped.geom_type in ("MultiPolygon", "GeometryCollection") else [clipped]
    polys = [g for g in geoms if g.geom_type == "Polygon" and g.exterior]
    polys.sort(key=lambda p: -p.area)
    rings = [[[round(x, 5), round(y, 5)] for x, y in p.exterior.coords]
             for p in polys if p.area >= minarea]
    if not rings and polys:                 # all slivers -> keep the largest
        p = polys[0]
        rings = [[[round(x, 5), round(y, 5)] for x, y in p.exterior.coords]]
    return rings

# ── Taxonomy: map checklist names to iNat-active taxa ─────────────────────────
# (Mirrors build_natives_csv.py — iNat's taxonomy, not POWO's.)
SPECIES_OVERRIDES = {
    "coryphantha alversonii":    "Escobaria alversonii",
    "coryphantha chlorantha":    "Escobaria chlorantha",
    "coryphantha dasyacantha":   "Escobaria dasyacantha",
    "coryphantha duncanii":      "Escobaria duncanii",
    "coryphantha missouriensis": "Escobaria missouriensis",
    "coryphantha sneedii":       "Escobaria sneedii",
    "coryphantha tuberculosa":   "Escobaria tuberculosa",
    "coryphantha vivipara":      "Escobaria vivipara",
    "sclerocactus brevihamatus": "Ancistrocactus brevihamatus",
    "sclerocactus scheeri":      "Ancistrocactus scheeri",
    "sclerocactus uncinatus":    "Glandulicactus uncinatus",
    "hamatocactus bicolor":      "Thelocactus bicolor",
    "echinocereus chisoensis":   "Echinocereus chisosensis",
    "escobaria robbinsorum":     "Escobaria robbinsiorum",
    "homalocephala polycephalus":"Homalocephala polycephala",
    "opuntia santarita":         "Opuntia santa-rita",
}
# Lumped infraspecific taxa: (iNat taxon name, iNat taxon ID)
VARIETY_OVERRIDES = {
    "cylindropuntia spinosior":  ("Cylindropuntia imbricata spinosior", 1039188),
    "cylindropuntia rosea":      ("Cylindropuntia imbricata rosea",     1039189),
    "cylindropuntia versicolor": ("Cylindropuntia thurberi versicolor", 1039186),
    "echinocereus fasciculatus": ("Echinocereus engelmannii fasciculatus", 856951),
    "mammillaria macdougalii":   ("Mammillaria heyderi macdougalii",    241640),
    "opuntia erinacea":          ("Opuntia polyacantha erinacea",       81159),
    "escobaria orcuttii":        ("Escobaria sneedii orcuttii",         871601),
    "escobaria guadalupensis":   ("Escobaria sneedii",                  162738),
}


# ── HTTP ──────────────────────────────────────────────────────────────────────
def fetch(url, retries=5):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def api_taxa(params, retries=4):
    url = "https://api.inaturalist.org/v1/taxa?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            return fetch(url).get("results", [])
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return []


# ── iNat ID resolution ────────────────────────────────────────────────────────
def _epithet(name):
    parts = name.replace("×", "").split()
    return parts[-1].lower() if parts else ""


def resolve_taxon_id(name, known_ids, cache):
    """Return (inat_id, inat_name) for a checklist species, or (None, None)."""
    key = name.lower()
    if key in cache:
        c = cache[key]
        return c["id"], c["name"]

    res = (None, None)
    if key in VARIETY_OVERRIDES:
        nm, tid = VARIETY_OVERRIDES[key]
        res = (tid, nm)
    elif key in known_ids:                      # already observed (authoritative)
        res = (known_ids[key], name)
    else:
        target = SPECIES_OVERRIDES.get(key, name)
        results = api_taxa({"q": target, "per_page": 10})
        # exact active species
        for t in results:
            if t["name"].lower() == target.lower() and t["is_active"]:
                res = (t["id"], t["name"]); break
        # genus move: active cactus species, same terminal epithet
        if res == (None, None):
            ep = _epithet(target)
            for t in results:
                anc = t.get("ancestor_ids") or []
                if (t["is_active"] and CACTACEAE in anc
                        and len(t["name"].split()) == 2 and _epithet(t["name"]) == ep):
                    res = (t["id"], t["name"]); break
        time.sleep(SLEEP)

    cache[key] = {"id": res[0], "name": res[1]}
    return res


# ── iNat community coordinates ──────────────────────────────────────────────────
def fetch_community_coords(inat_taxon_id):
    coords, page, per_page = [], 1, 200
    while True:
        params = {
            "taxon_id": inat_taxon_id, "quality_grade": "research",
            "per_page": per_page, "page": page,
            "order_by": "id", "order": "asc", "geo": "true",
        }
        data = fetch("https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(params))
        results = data.get("results", [])
        total = data.get("total_results", 0)
        for obs in results:
            loc = obs.get("location")
            if loc:
                try:
                    lat, lng = loc.split(",")
                    coords.append((float(lng), float(lat)))
                except ValueError:
                    pass
        if page * per_page >= total or page * per_page >= MAX_OBS_PER_SPECIES or not results:
            break
        page += 1
        time.sleep(SLEEP)
    return coords


# ── Grubbs outlier rejection (iterative, two-sided) ─────────────────────────────
def grubbs_filter(coords, alpha=GRUBBS_ALPHA):
    """Remove geographic outliers. Each iteration drops the single most extreme
    point (standardised, in lng or lat) if it exceeds the Grubbs critical value.
    Returns (kept_coords, n_removed)."""
    pts = np.asarray(coords, dtype=float)
    if len(pts) < MIN_POINTS_FOR_GRUBBS:
        return [tuple(p) for p in pts], 0

    keep = np.ones(len(pts), dtype=bool)
    removed = 0
    while keep.sum() > MIN_POINTS_FOR_GRUBBS:
        idx = np.where(keep)[0]
        sub = pts[idx]
        n = len(sub)
        t = stats.t.ppf(1 - alpha / (2 * n), n - 2)
        g_crit = (n - 1) / np.sqrt(n) * np.sqrt(t**2 / (n - 2 + t**2))

        worst = None  # (G, original_index)
        for d in (0, 1):
            x = sub[:, d]
            sd = x.std(ddof=1)
            if sd == 0:
                continue
            dev = np.abs(x - x.mean()) / sd
            j = int(dev.argmax())
            if dev[j] > g_crit and (worst is None or dev[j] > worst[0]):
                worst = (dev[j], idx[j])
        if worst is None:
            break
        keep[worst[1]] = False
        removed += 1

    return [tuple(p) for p in pts[keep]], removed


# ── Convex hull (Andrew's monotone chain) ────────────────────────────────────────
def cross(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])


def convex_hull(points):
    pts = sorted(set(points))
    if len(pts) < MIN_POINTS_FOR_HULL:
        return None

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and cross(h[-2], h[-1], p) <= 0:
                h.pop()
            h.append(p)
        return h

    lower = half(pts)
    upper = half(list(reversed(pts)))
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return None
    hull.append(hull[0])
    return hull


# ── Main ────────────────────────────────────────────────────────────────────────
def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main():
    print("\n[xena] Xena — range builder (Grubbs outlier rejection)\n")
    if not DATA_PATH.exists():
        print(f"X {DATA_PATH} not found. Run sync.py first.")
        return

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    checklist = data.get("checklist", [])
    taxa = data.get("taxa", [])

    known_ids = {t["name"].lower(): t["inat_id"] for t in taxa
                 if t.get("name") and t.get("inat_id")}
    id_cache = load_json(IDS_CACHE, {})
    coords_cache = load_json(COORDS_CACHE, {})

    # 1) Resolve every checklist species to an iNat taxon ID
    print(f"Resolving iNat IDs for {len(checklist)} checklist species…")
    resolved = {}   # inat_id -> {name, inat_name}
    for c in checklist:
        tid, inat_name = resolve_taxon_id(c["name"], known_ids, id_cache)
        if tid is not None:
            resolved.setdefault(tid, {"name": c["name"], "inat_name": inat_name})
    IDS_CACHE.write_text(json.dumps(id_cache, indent=2), encoding="utf-8")
    print(f"  -> {len(resolved)} unique iNat taxa\n")

    # Ranges are written to their OWN file (ranges.json) so the per-deploy
    # `sync.py` rebuild of data.json never clobbers them. Each range carries
    # its display_name, so the frontend can match by id (observed taxa) or by
    # name (checklist species) without data.json needing any extra fields.
    def save_ranges():
        RANGES_PATH.write_text(json.dumps({
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ranges": ranges,
        }, indent=2), encoding="utf-8")

    # 2-4) Fetch, Grubbs-filter, refined hull (concave + land clip)
    land = get_land_mask()
    ranges = {}                               # rebuild fresh (cheap from cache)
    items = list(resolved.items())
    for i, (tid, meta) in enumerate(items, 1):
        name = meta["name"]
        print(f"[{i}/{len(items)}] {name} (taxon {tid})", flush=True)

        ck = str(tid)
        try:
            if ck in coords_cache:
                coords = [tuple(p) for p in coords_cache[ck]]
                print(f"    {len(coords)} sightings (cached)", flush=True)
            else:
                coords = fetch_community_coords(tid)
                coords_cache[ck] = coords
                COORDS_CACHE.write_text(json.dumps(coords_cache), encoding="utf-8")
                print(f"    {len(coords)} sightings (fetched)", flush=True)
                time.sleep(SLEEP)
        except Exception as e:
            print(f"    ! fetch failed ({e}); skipping", flush=True)
            continue

        if len(coords) < MIN_POINTS_FOR_HULL:
            print("    ! too few points, skipping", flush=True)
            continue

        kept, removed = grubbs_filter(coords)
        rings = refined_polygons(kept, land)
        if not rings:
            print("    ! degenerate hull, skipping", flush=True)
            continue

        rx = [x for r in rings for x, _ in r]; ry = [y for r in rings for _, y in r]
        kxs = [p[0] for p in kept]; kys = [p[1] for p in kept]
        ranges[str(tid)] = {
            "taxon_name":      meta["inat_name"] or name,
            "display_name":    name,
            "source_points":   len(coords),
            "kept_points":     len(kept),
            "outliers_removed": removed,
            "polygons":        rings,                # one or more exterior rings (land-clipped)
            "polygon":         rings[0],             # largest ring (back-compat)
            "bbox":            [round(min(rx), 5), round(min(ry), 5),
                                round(max(rx), 5), round(max(ry), 5)],
            "centroid":        [round(sum(kxs)/len(kxs), 5), round(sum(kys)/len(kys), 5)],
        }
        print(f"    OK {len(coords)}->{len(kept)} pts ({removed} outliers), "
              f"{len(rings)} polygon(s)", flush=True)

        if i % 8 == 0:         # frequent checkpoint — background procs die ~35min
            save_ranges()

    save_ranges()

    print("\n=== SUMMARY ===")
    print(f"  Ranges built: {len(ranges)} / {len(items)} taxa")
    print(f"  Saved to: {RANGES_PATH}")


if __name__ == "__main__":
    main()
