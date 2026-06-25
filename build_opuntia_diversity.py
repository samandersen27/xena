"""
Splitter's Opuntia diversity map.

Species set = Opuntia taxa recognized on Opuntia Web (opuntiads.com) that are
ALSO active species on iNaturalist (the intersection). For each, pull community
sightings, Grubbs-reject outliers, build a convex-hull range, then count
overlapping ranges on a grid across the SW states.

Reads:  opuntiads.com sitemap, iNaturalist API, coords_cache.json (shared)
Writes: frontend/public/opuntia_ranges.json
        frontend/public/opuntia_richness.json
Caches: coords_cache.json (shared with build_ranges), opuntia_ids.json
"""

import json, re, time, urllib.request
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MplPath

from build_ranges import (
    api_taxa, fetch_community_coords, grubbs_filter,
    get_land_mask, refined_polygons,
    COORDS_CACHE, CACTACEAE, SLEEP, MIN_POINTS_FOR_HULL,
)

HERE        = Path(__file__).parent / "frontend" / "public"
RANGES_OUT  = HERE / "opuntia_ranges.json"
RICH_OUT    = HERE / "opuntia_richness.json"
STATES      = HERE / "sw_states.json"
IDS_CACHE   = Path(__file__).parent / "opuntia_ids.json"
SITEMAP     = "https://www.opuntiads.com/page-sitemap.xml"
HEADERS     = {"User-Agent": "Mozilla/5.0 (Xena-CactusMuseum)"}

# SW window + grid (same as build_richness)
WEST, EAST, SOUTH, NORTH = -125.0, -93.0, 25.0, 43.0
RES = 0.1

# Tokens in page slugs that are NOT part of a species epithet
STOP = {
    "pricklypear", "cactus", "beavertail", "low", "dark", "spine", "blue",
    "western", "test", "incl", "o", "sp", "nova", "aff", "subarmata",
    "cold", "hardy", "hot", "2",
}


def slug_epithets(slug):
    """From an opuntiads page slug, yield candidate species epithets."""
    s = slug.strip().lower()
    for pre in ("opuntia-", "opunia-", "opunti-", "opuntdia-"):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    else:
        return []
    toks = []
    for t in s.split("-"):
        if t in STOP or t.isdigit() or not t.isalpha():
            break
        toks.append(t)
    if not toks:
        return []
    # try the single first epithet and the full hyphenated form
    cands = {toks[0]}
    if len(toks) > 1:
        cands.add("-".join(toks[:2]))
        cands.add("-".join(toks))
    return cands


def fetch_opuntiaweb_epithets():
    req = urllib.request.Request(SITEMAP, headers=HEADERS)
    xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    slugs = re.findall(r"opuntiads\.com/([a-z0-9\-]*opun[a-z0-9\-]+)/", xml)
    eps = set()
    for sl in slugs:
        eps |= set(slug_epithets(sl))
    return sorted(eps)


def load_json(p, d):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d


def resolve_opuntia(epithets, cache):
    """Return {inat_id: name} for candidate epithets that are active iNat
    Opuntia species (the Opuntia-Web ∩ iNat intersection)."""
    found = {}
    for ep in epithets:
        name = f"Opuntia {ep}"
        key = name.lower()
        if key in cache:
            tid = cache[key]
        else:
            tid = None
            for t in api_taxa({"q": name, "per_page": 8}):
                if (t["name"].lower() == key and t["is_active"]
                        and t.get("rank") == "species"
                        and CACTACEAE in (t.get("ancestor_ids") or [])):
                    tid = t["id"]; break
            cache[key] = tid
            time.sleep(SLEEP)
        if tid:
            found[tid] = name
    return found


def build_ranges(species):
    coords_cache = load_json(COORDS_CACHE, {})
    land = get_land_mask()
    ranges = {}
    items = list(species.items())
    for i, (tid, name) in enumerate(items, 1):
        ck = str(tid)
        print(f"[{i}/{len(items)}] {name} ({tid})", flush=True)
        if ck in coords_cache:
            coords = [tuple(p) for p in coords_cache[ck]]
            print(f"    {len(coords)} sightings (cached)", flush=True)
        else:
            try:
                coords = fetch_community_coords(tid)
            except Exception as e:
                print(f"    ! fetch failed ({e}); skipping", flush=True); continue
            coords_cache[ck] = coords
            COORDS_CACHE.write_text(json.dumps(coords_cache), encoding="utf-8")
            print(f"    {len(coords)} sightings (fetched)", flush=True)
            time.sleep(SLEEP)
        if len(coords) < MIN_POINTS_FOR_HULL:
            print("    ! too few points", flush=True); continue
        kept, removed = grubbs_filter(coords)
        rings = refined_polygons(kept, land)
        if not rings:
            print("    ! degenerate hull", flush=True); continue
        rx = [x for r in rings for x, _ in r]; ry = [y for r in rings for _, y in r]
        kxs = [p[0] for p in kept]; kys = [p[1] for p in kept]
        ranges[str(tid)] = {
            "taxon_name": name, "display_name": name,
            "source_points": len(coords), "kept_points": len(kept),
            "outliers_removed": removed,
            "polygons": rings, "polygon": rings[0],
            "bbox": [round(min(rx), 5), round(min(ry), 5), round(max(rx), 5), round(max(ry), 5)],
            "centroid": [round(sum(kxs)/len(kxs), 5), round(sum(kys)/len(kys), 5)],
        }
        print(f"    OK {len(coords)}->{len(kept)} pts ({removed} outliers), {len(rings)} poly(s)", flush=True)
        if i % 8 == 0:
            RANGES_OUT.write_text(json.dumps({"ranges": ranges}, indent=2), encoding="utf-8")
    RANGES_OUT.write_text(json.dumps({"ranges": ranges}, indent=2), encoding="utf-8")
    return ranges


def build_richness(ranges):
    states = json.loads(STATES.read_text(encoding="utf-8"))
    xs = np.arange(WEST, EAST + RES, RES)
    ys = np.arange(SOUTH, NORTH + RES, RES)
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys)
    pts = np.column_stack([X.ravel(), Y.ravel()])
    counts = np.zeros(pts.shape[0], dtype=np.int32)
    for r in ranges.values():
        inside = np.zeros(pts.shape[0], dtype=bool)
        for ring in r.get("polygons") or [r.get("polygon")]:
            if ring and len(ring) >= 4:
                inside |= MplPath(ring).contains_points(pts)
        counts += inside
    inside = np.zeros(pts.shape[0], dtype=bool)
    for s in states:
        for ring in s.get("rings", []):
            if len(ring) >= 4:
                inside |= MplPath(ring).contains_points(pts)
    counts[~inside] = -1
    grid = counts.reshape(ny, nx)
    RICH_OUT.write_text(json.dumps({
        "res": RES, "bbox": [WEST, SOUTH, EAST, NORTH], "nx": nx, "ny": ny,
        "max": int(counts.max()), "data": grid.astype(int).tolist(),
    }), encoding="utf-8")
    print(f"richness: {nx}x{ny}, max {counts.max()} overlapping Opuntia", flush=True)


def main():
    print("Fetching Opuntia Web species list…", flush=True)
    eps = fetch_opuntiaweb_epithets()
    print(f"  {len(eps)} candidate epithets from opuntiads.com", flush=True)

    cache = load_json(IDS_CACHE, {})
    print("Resolving against iNaturalist (active species only)…", flush=True)
    species = resolve_opuntia(eps, cache)
    IDS_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    print(f"  -> {len(species)} Opuntia Web species are active on iNaturalist", flush=True)
    for tid, nm in sorted(species.items(), key=lambda kv: kv[1]):
        print(f"     {nm}  ({tid})", flush=True)

    ranges = build_ranges(species)
    build_richness(ranges)
    print(f"\nDone. {len(ranges)} ranges -> {RANGES_OUT.name}, {RICH_OUT.name}", flush=True)


if __name__ == "__main__":
    main()
