"""
Xena — range polygon builder
For each species you've observed (research grade), pulls ALL community
sightings from iNaturalist (not just yours) and computes a convex hull
polygon approximating that species' geographic range.

This is the algorithm Sam originally described:
  - Collect all sighting coordinates for a species
  - Find the outermost points in every direction
  - Connect them into a closed polygon
  - That polygon approximates the species' range

No third-party packages required — the convex hull (Andrew's monotone
chain algorithm) is implemented from scratch below.

Run with: python build_ranges.py
Reads:  frontend/public/data.json   (must run sync.py first)
Writes: frontend/public/data.json   (adds a "ranges" key)
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

DATA_PATH = Path(__file__).parent / "frontend" / "public" / "data.json"
HEADERS   = {"User-Agent": "Xena-CactusMuseum/0.1"}
SLEEP     = 1.1     # iNat rate limit — ~1 req/sec
MIN_POINTS_FOR_HULL = 3
MAX_OBS_PER_SPECIES  = 2000   # cap to keep runtime reasonable


# ── Convex hull (Andrew's monotone chain) ────────────────────────────────────
# Pure Python, no numpy/shapely needed.
# Input: list of (x, y) tuples — here (longitude, latitude)
# Output: list of (x, y) tuples forming the hull, in order, closed ring

def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(points):
    """
    Returns the convex hull of a set of 2D points as a closed ring
    (first point repeated at the end), or None if fewer than 3
    distinct points are given.
    """
    pts = sorted(set(points))
    if len(pts) < MIN_POINTS_FOR_HULL:
        return None

    def build_half(seq):
        half = []
        for p in seq:
            while len(half) >= 2 and cross(half[-2], half[-1], p) <= 0:
                half.pop()
            half.append(p)
        return half

    lower = build_half(pts)
    upper = build_half(list(reversed(pts)))
    hull  = lower[:-1] + upper[:-1]

    if len(hull) < 3:
        return None

    hull.append(hull[0])  # close the ring
    return hull


# ── iNat fetch ────────────────────────────────────────────────────────────────

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_community_coords(inat_taxon_id: int) -> list:
    """
    Pull ALL research-grade community observations (not just Sam's) for a
    species, across the whole iNat userbase, and return (lng, lat) tuples.
    """
    coords = []
    page    = 1
    per_page = 200

    while True:
        params = {
            "taxon_id":      inat_taxon_id,
            "quality_grade": "research",
            "per_page":      per_page,
            "page":          page,
            "order_by":      "id",
            "order":         "asc",
            "geo":           "true",   # only obs with coordinates
        }
        url  = "https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(params)
        data = fetch(url)

        results = data.get("results", [])
        total   = data.get("total_results", 0)

        for obs in results:
            loc = obs.get("location")
            if loc:
                try:
                    lat, lng = loc.split(",")
                    coords.append((float(lng), float(lat)))  # (x=lng, y=lat)
                except ValueError:
                    pass

        fetched = page * per_page
        if fetched >= total or fetched >= MAX_OBS_PER_SPECIES or not results:
            break

        page += 1
        time.sleep(SLEEP)

    return coords


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🌵 Xena — range polygon builder\n")

    if not DATA_PATH.exists():
        print(f"✗ {DATA_PATH} not found. Run sync.py first.")
        return

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    taxa = data.get("taxa", [])

    # Only build ranges for species you've actually observed
    observed_taxa = [t for t in taxa if t.get("rank") == "species" and t.get("obs_count", 0) > 0]
    print(f"  Building ranges for {len(observed_taxa)} observed species\n")

    ranges = {}

    for i, taxon in enumerate(observed_taxa, 1):
        name     = taxon.get("name", "?")
        inat_id  = taxon.get("inat_id")
        print(f"[{i}/{len(observed_taxa)}] {name}...")

        if not inat_id:
            print(f"    ⚠ no iNat ID, skipping")
            continue

        coords = fetch_community_coords(inat_id)
        print(f"    {len(coords)} community sightings with coordinates")

        hull = convex_hull(coords)
        if hull is None:
            print(f"    ⚠ not enough points for a polygon (need {MIN_POINTS_FOR_HULL}+)")
            continue

        # Store as GeoJSON-style polygon: [[lng, lat], [lng, lat], ...]
        ranges[str(inat_id)] = {
            "taxon_name":   name,
            "source_points": len(coords),
            "polygon":      [[round(x, 5), round(y, 5)] for x, y in hull],
        }
        print(f"    ✓ polygon with {len(hull)} vertices")

        time.sleep(SLEEP)

    # Merge into data.json
    data["ranges"] = ranges
    data["ranges_built_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    DATA_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"\n=== SUMMARY ===")
    print(f"  Species with ranges built: {len(ranges)}")
    print(f"  Saved to: {DATA_PATH}")
    print(f"\n✓ Done. Refresh the app to see range polygons on species pages.\n")


if __name__ == "__main__":
    main()
