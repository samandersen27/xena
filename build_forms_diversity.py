"""
Opuntia "form" diversity — lemonadeberry.weebly.com morphotypes as a taxonomy.

The author tracks ~40 SoCal Opuntia morphotypes ("forms"), each as its own
iNaturalist project. We treat each project as a form, pull its georeferenced
observations, build a refined range (concave hull + land clip), then count
overlapping forms on a grid -> a "form biodiversity" contour.

Reads:  _forms_page.html (saved page), iNaturalist API
Writes: frontend/public/forms_ranges.json, frontend/public/forms_richness.json
Cache:  _forms_cache.json
"""
import re, json, time, urllib.request
from pathlib import Path
import numpy as np, shapely
from shapely.geometry import MultiPoint, box
from matplotlib.path import Path as MP
from build_ranges import grubbs_filter, refined_polygons, get_land_mask

HERE = Path(__file__).parent
PAGE = HERE / "_forms_page.html"
CACHE = HERE / "_forms_cache.json"
RANGES_OUT = HERE / "frontend" / "public" / "forms_ranges.json"
RICH_OUT   = HERE / "frontend" / "public" / "forms_richness.json"
UA = {"User-Agent": "Xena-CactusMuseum"}
# SoCal window (forms are coastal SoCal)
W, E, S, N = -121.0, -115.9, 32.3, 35.3
RES = 0.05   # ~5.5 km cells (finer, since the area is small)

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def api(url, retries=4):
    for a in range(retries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code == 422:
                return None
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None


def form_key(slug):
    s = re.sub(r'-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', '', slug)
    return s


def display_name(key):
    if key.startswith("opuntia-form-"):
        code = key[len("opuntia-form-"):]
        if len(code) == 1: return f"Form {code.upper()}"
        if len(code) == 2 and code[0] in "ab": return f"Form {code[0]}{code[1].upper()}"
        return f"Form {code}"
    return key.replace("-", " ").title()


def project_slugs():
    html = PAGE.read_text(encoding="utf-8", errors="ignore")
    slugs = set(re.findall(r'inaturalist\.org/projects/([a-z0-9-]+)', html))
    slugs = {s.rstrip('-') for s in slugs if s not in ('opuntia-form',)}
    # group by form key, prefer the variant that returns the most observations
    keys = {}
    for s in slugs:
        keys.setdefault(form_key(s), set()).add(s)
    return keys


def fetch_form(slugs):
    """Try candidate slugs; return (coords, used_slug)."""
    best = ([], None)
    for slug in sorted(slugs, key=len):
        ck = f"proj_{slug}"
        if ck in cache:
            coords = [tuple(p) for p in cache[ck]]
        else:
            coords, page = [], 1
            while True:
                d = api(f"https://api.inaturalist.org/v1/observations?project_id={slug}"
                        f"&geo=true&per_page=200&page={page}")
                if not d:
                    break
                res = d.get("results", [])
                for o in res:
                    loc = o.get("location")
                    if loc:
                        la, lo = loc.split(",")
                        coords.append((float(lo), float(la)))
                if page * 200 >= d.get("total_results", 0) or not res or page >= 3:
                    break
                page += 1; time.sleep(0.6)
            cache[ck] = coords; CACHE.write_text(json.dumps(cache)); time.sleep(0.4)
        if len(coords) > len(best[0]):
            best = (coords, slug)
    return best


def buffered(points):
    mp = MultiPoint([tuple(p) for p in points])
    g = mp.buffer(0.022)
    return g


def main():
    land = get_land_mask()
    keys = project_slugs()
    print(f"{len(keys)} candidate forms (projects)\n")
    forms = {}
    for i, (key, slugs) in enumerate(sorted(keys.items()), 1):
        coords, used = fetch_form(slugs)
        if not coords:
            print(f"[{i}/{len(keys)}] {key}: no geo obs, skip"); continue
        # keep SoCal-region points; Grubbs only if enough
        pts = [(x, y) for x, y in coords if -122 <= x <= -114 and 31 <= y <= 36]
        if len(pts) < 1:
            print(f"[{i}/{len(keys)}] {key}: out of region, skip"); continue
        kept, _ = grubbs_filter(pts) if len(pts) >= 7 else (pts, 0)
        if len(kept) >= 4:
            rings = refined_polygons(kept, land)
        else:
            g = buffered(kept).intersection(land)
            geoms = g.geoms if g.geom_type == 'MultiPolygon' else [g]
            rings = [[[round(x, 5), round(y, 5)] for x, y in gg.exterior.coords]
                     for gg in geoms if gg.geom_type == 'Polygon' and gg.exterior]
        if not rings:
            print(f"[{i}/{len(keys)}] {key}: degenerate, skip"); continue
        rx = [x for r in rings for x, _ in r]; ry = [y for r in rings for _, y in r]
        forms[key] = {
            "display_name": display_name(key), "project": used,
            "n": len(kept), "polygons": rings,
            "bbox": [round(min(rx), 5), round(min(ry), 5), round(max(rx), 5), round(max(ry), 5)],
        }
        print(f"[{i}/{len(keys)}] {display_name(key)}: {len(kept)} obs, {len(rings)} poly(s)")

    RANGES_OUT.write_text(json.dumps({"ranges": forms}, indent=1), encoding="utf-8")
    print(f"\n{len(forms)} forms with ranges -> {RANGES_OUT.name}")

    # richness: overlapping form polygons on a SoCal grid, clipped to land
    xs = np.arange(W, E + RES, RES); ys = np.arange(S, N + RES, RES)
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys); pts = np.column_stack([X.ravel(), Y.ravel()])
    counts = np.zeros(pts.shape[0], dtype=np.int32)
    for f in forms.values():
        inside = np.zeros(pts.shape[0], dtype=bool)
        for ring in f["polygons"]:
            if len(ring) >= 4:
                inside |= MP(ring).contains_points(pts)
        counts += inside
    landmask = np.zeros(pts.shape[0], bool)
    lg = land.intersection(box(W, S, E, N))
    for g in (lg.geoms if lg.geom_type == 'MultiPolygon' else [lg]):
        if g.geom_type == 'Polygon':
            landmask |= MP(np.array(g.exterior.coords)).contains_points(pts)
    counts[~landmask] = -1
    grid = counts.reshape(ny, nx)
    RICH_OUT.write_text(json.dumps({
        "res": RES, "bbox": [W, S, E, N], "nx": nx, "ny": ny,
        "max": int(counts.max()), "data": grid.astype(int).tolist()}), encoding="utf-8")
    print(f"richness: {nx}x{ny}, max {counts.max()} overlapping forms -> {RICH_OUT.name}")


if __name__ == "__main__":
    main()
