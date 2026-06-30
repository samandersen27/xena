"""
Cholla diversity map — Cholla Web (opuntiads.com/cyl/) ∩ iNaturalist.

Mirror of build_opuntia_diversity.py but for the chollas: every
Cylindropuntia / Grusonia / Corynopuntia / Micropuntia taxon catalogued on
Cholla Web that iNaturalist also treats as a valid species. Refined ranges
(concave hull + land clip), then overlapping-range richness over the SW states.

Reads:  _cholla_page.html (saved opuntiads.com/cyl/ page), iNaturalist API
Writes: frontend/public/cholla_ranges.json, frontend/public/cholla_richness.json
Cache:  coords_cache.json (shared), cholla_ids.json
"""
import re, json, time
from pathlib import Path
import numpy as np
from matplotlib.path import Path as MplPath
from build_ranges import (api_taxa, fetch_community_coords, grubbs_filter,
                          get_land_mask, refined_polygons, COORDS_CACHE, CACTACEAE,
                          SLEEP, MIN_POINTS_FOR_HULL)

HERE = Path(__file__).parent
PAGE = HERE / "_cholla_page.html"
RANGES_OUT = HERE / "frontend" / "public" / "cholla_ranges.json"
RICH_OUT   = HERE / "frontend" / "public" / "cholla_richness.json"
STATES     = HERE / "frontend" / "public" / "sw_states.json"
IDS_CACHE  = HERE / "cholla_ids.json"

WEST, EAST, SOUTH, NORTH = -125.0, -93.0, 25.0, 43.0
RES = 0.1

GENUS = {"cylindropuntia": "Cylindropuntia", "corynopuntia": "Corynopuntia",
         "grusonia": "Grusonia", "micropuntia": "Micropuntia", "c": "Cylindropuntia"}
CHOLLA_GENERA = {"Cylindropuntia", "Grusonia", "Corynopuntia", "Micropuntia"}
EPITHET_FIX = {"abysii": "abyssi", "multigenticulata": "multigeniculata", "wolfi": "wolfii"}

cache = json.loads(IDS_CACHE.read_text()) if IDS_CACHE.exists() else {}


def species_from_page():
    """Return list of (display_genus, epithet) from the /cyl/ species links."""
    html = PAGE.read_text(encoding="utf-8", errors="ignore")
    slugs = set(re.findall(r'/cyl/([a-z][a-z0-9-]+)/', html))
    out = {}
    for s in slugs:
        toks = s.split("-")
        if toks[0] not in GENUS or len(toks) < 2:
            continue
        ep = toks[1]
        ep = EPITHET_FIX.get(ep, ep)
        if not ep.isalpha():
            continue
        out[(GENUS[toks[0]], ep)] = True
    return sorted(out)


def epithet(name):
    p = name.split()
    return p[-1].lower() if p else ""


def resolve(genus, ep):
    key = f"{genus} {ep}".lower()
    if key in cache:
        return cache[key]
    res = None
    queries = [f"{genus} {ep}", f"Grusonia {ep}", f"Cylindropuntia {ep}", f"Micropuntia {ep}"]
    seen = set()
    for q in queries:
        if q in seen:
            continue
        seen.add(q)
        for t in api_taxa({"q": q, "per_page": 8}):
            anc = t.get("ancestor_ids") or []
            g = t["name"].split()[0]
            if (t["is_active"] and t.get("rank") == "species" and CACTACEAE in anc
                    and g in CHOLLA_GENERA and epithet(t["name"]) == ep):
                res = {"id": t["id"], "name": t["name"]}
                break
        if res:
            break
        time.sleep(SLEEP)
    cache[key] = res
    IDS_CACHE.write_text(json.dumps(cache, indent=1))
    return res


def load_json(p, d):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d


def main():
    land = get_land_mask()
    coords_cache = load_json(COORDS_CACHE, {})
    species = species_from_page()
    print(f"{len(species)} cholla taxa on Cholla Web\n")

    resolved = {}
    for g, ep in species:
        r = resolve(g, ep)
        if r:
            resolved.setdefault(r["id"], r["name"])
        else:
            print(f"  !? {g} {ep}: not active on iNat")
    print(f"\n{len(resolved)} resolve to active iNat cholla species\n")

    ranges = {}
    for i, (tid, name) in enumerate(sorted(resolved.items(), key=lambda kv: kv[1]), 1):
        ck = str(tid)
        if ck in coords_cache:
            coords = [tuple(p) for p in coords_cache[ck]]
            tag = "cached"
        else:
            try:
                coords = fetch_community_coords(tid)
            except Exception as e:
                print(f"[{i}] {name}: fetch failed ({e})"); continue
            coords_cache[ck] = coords
            COORDS_CACHE.write_text(json.dumps(coords_cache)); time.sleep(SLEEP)
            tag = "fetched"
        if len(coords) < MIN_POINTS_FOR_HULL:
            print(f"[{i}] {name}: too few points"); continue
        kept, removed = grubbs_filter(coords)
        rings = refined_polygons(kept, land)
        if not rings:
            print(f"[{i}] {name}: degenerate"); continue
        rx = [x for r in rings for x, _ in r]; ry = [y for r in rings for _, y in r]
        ranges[str(tid)] = {
            "taxon_name": name, "display_name": name,
            "source_points": len(coords), "kept_points": len(kept),
            "outliers_removed": removed, "polygons": rings, "polygon": rings[0],
            "bbox": [round(min(rx), 5), round(min(ry), 5), round(max(rx), 5), round(max(ry), 5)],
        }
        print(f"[{i}] {name}: {len(kept)} pts, {len(rings)} poly(s) ({tag})")

    RANGES_OUT.write_text(json.dumps({"ranges": ranges}, indent=1), encoding="utf-8")
    print(f"\n{len(ranges)} cholla ranges -> {RANGES_OUT.name}")

    # richness over SW states
    states = json.loads(STATES.read_text(encoding="utf-8"))
    xs = np.arange(WEST, EAST + RES, RES); ys = np.arange(SOUTH, NORTH + RES, RES)
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys); pts = np.column_stack([X.ravel(), Y.ravel()])
    counts = np.zeros(pts.shape[0], dtype=np.int32)
    for r in ranges.values():
        inside = np.zeros(pts.shape[0], dtype=bool)
        for ring in r["polygons"]:
            if len(ring) >= 4:
                inside |= MplPath(ring).contains_points(pts)
        counts += inside
    sw = np.zeros(pts.shape[0], bool)
    for st in states:
        for ring in st.get("rings", []):
            if len(ring) >= 4:
                sw |= MplPath(ring).contains_points(pts)
    counts[~sw] = -1
    grid = counts.reshape(ny, nx)
    RICH_OUT.write_text(json.dumps({
        "res": RES, "bbox": [WEST, SOUTH, EAST, NORTH], "nx": nx, "ny": ny,
        "max": int(counts.max()), "data": grid.astype(int).tolist()}), encoding="utf-8")
    print(f"richness: {nx}x{ny}, max {counts.max()} overlapping chollas -> {RICH_OUT.name}")


if __name__ == "__main__":
    main()
