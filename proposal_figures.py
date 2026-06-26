"""
Research-grade proposal figures for the coastal SoCal Opuntia complex.
Builds, into frontend/public/figures/:
  fig_hybrid.png   - hybrid complex (ranges, hybrids, hotspot KDE)
  fig_phenology.png- flowering phenology ridgelines + rose
  fig_effort.png   - effort-corrected relative occurrence (target-group bg)
  fig_niche.png    - coastal niche (distance-to-coast x elevation) + Schoener's D
Caches all iNat/elevation pulls so reruns are cheap.
"""
import json, time, urllib.request, urllib.parse
from pathlib import Path
import numpy as np, shapely, shapely.ops
from shapely.geometry import MultiPoint, box, Point
from scipy.stats import gaussian_kde
from matplotlib.path import Path as MP
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Ellipse
from build_ranges import grubbs_filter, refined_polygons, get_land_mask, COORDS_CACHE

HERE = Path(__file__).parent
FIGS = HERE / "frontend" / "public" / "figures"; FIGS.mkdir(parents=True, exist_ok=True)
CACHE = HERE / "_proposal_cache.json"
UA = {"User-Agent": "Xena-CactusMuseum"}

PARENTS = [("Opuntia littoralis", 78266, "#d7191c"), ("Opuntia oricola", 47896, "#2c7bb6"),
           ("Opuntia semispinosa", 841133, "#1a9641")]
HYBRIDS = [("O. × occidentalis", 181539, "#7b3294", "o"), ("O. × vaseyi", 181540, "#e66101", "^"),
           ("O. × demissa", 170896, "#018571", "s")]
ALLTAXA = [("Opuntia littoralis", 78266, "#d7191c"), ("Opuntia oricola", 47896, "#2c7bb6"),
           ("Opuntia semispinosa", 841133, "#1a9641"), ("Opuntia × occidentalis", 181539, "#7b3294"),
           ("Opuntia × vaseyi", 181540, "#e66101"), ("Opuntia × demissa", 170896, "#018571")]
W, E, S, N = -120.6, -116.4, 32.45, 34.95
OPUNTIA_GENUS = 47902

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
def save_cache(): CACHE.write_text(json.dumps(cache))
def api(url, retries=6):
    for attempt in range(retries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(5 * (attempt + 1)); continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1)); continue
            raise

coords = json.loads(COORDS_CACHE.read_text())
land = get_land_mask()
coast_box = land.intersection(box(W - 0.3, S - 0.3, E + 0.3, N + 0.3))

def taxon_pts(tid):
    p = [(x, y) for x, y in coords[str(tid)] if W <= x <= E and S <= y <= N]
    k, _ = grubbs_filter(p); return np.array(k)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.linewidth': 0.6})
ASPECT = 1 / np.cos(np.radians((S + N) / 2))
CITIES = [("Santa Barbara", -119.70, 34.42), ("Los Angeles", -118.24, 34.05),
          ("Riverside", -117.40, 33.95), ("San Diego", -117.16, 32.72)]

def basemap(ax):
    ax.set_facecolor("#cfe2f3")
    for g in (coast_box.geoms if coast_box.geom_type == 'MultiPolygon' else [coast_box]):
        xs, ys = g.exterior.xy; ax.fill(xs, ys, fc="#f4f1ea", ec="#b9b09c", lw=0.5, zorder=0)
    for nm, x, y in CITIES:
        ax.plot(x, y, 'o', ms=3, mfc='#333', mec='white', mew=0.5, zorder=6)
        ax.annotate(nm, (x, y), xytext=(3, 3), textcoords='offset points', fontsize=6.5, zorder=6)
    ax.set_xlim(W, E); ax.set_ylim(S, N); ax.set_aspect(ASPECT)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_edgecolor('#888')

def scalebar(ax):
    deg = 50 / 111.0; x0, y0 = W + 0.15, S + 0.12
    ax.plot([x0, x0 + deg], [y0, y0], 'k-', lw=2, zorder=7)
    ax.text(x0 + deg / 2, y0 + 0.04, "50 km", ha='center', fontsize=6.5, zorder=7)


# ---------------------------------------------------------------- HYBRID
def fig_hybrid():
    pr, pp = {}, {}
    for n, t, c in PARENTS:
        pp[n] = taxon_pts(t); pr[n] = refined_polygons([tuple(p) for p in pp[n]], land)
    hp = {n: taxon_pts(t) for n, t, c, m in HYBRIDS}
    allh = np.vstack([v for v in hp.values() if len(v)])
    up = lambda rings: shapely.union_all([shapely.Polygon(r) for r in rings])
    overlap = up(pr["Opuntia littoralis"]).intersection(up(pr["Opuntia oricola"]))
    pct = 100 * sum(overlap.contains(Point(*p)) for p in allh) / len(allh)

    fig, ax = plt.subplots(1, 3, figsize=(13.5, 5.2), dpi=160)
    a = ax[0]; basemap(a)
    for n, t, c in PARENTS:
        for r in pr[n]: a.fill([p[0] for p in r], [p[1] for p in r], fc=c, ec=c, alpha=0.22, lw=1, zorder=2)
        a.scatter(pp[n][:, 0], pp[n][:, 1], s=2, c=c, alpha=0.35, lw=0, zorder=3)
    for g in (overlap.geoms if overlap.geom_type == 'MultiPolygon' else [overlap]):
        if not g.is_empty:
            xs, ys = g.exterior.xy; a.fill(xs, ys, fc='none', ec='k', lw=1.1, ls=(0, (4, 2)), zorder=4)
    a.set_title("A  Parental ranges & sympatry", fontsize=9.5, loc='left', fontweight='bold')
    a.legend(handles=[Patch(fc=c, alpha=0.5, label=n) for n, t, c in PARENTS] +
             [plt.Line2D([], [], ls=(0, (4, 2)), color='k', label='littoralis × oricola overlap')],
             loc='lower right', fontsize=6.3, framealpha=0.9); scalebar(a)
    a = ax[1]; basemap(a)
    for n, t, c in PARENTS:
        for r in pr[n]: a.plot([p[0] for p in r], [p[1] for p in r], c=c, lw=0.9, alpha=0.6, zorder=2)
    for n, t, c, m in HYBRIDS:
        H = hp[n]
        if len(H): a.scatter(H[:, 0], H[:, 1], s=16, marker=m, facecolor=c, edgecolor='white', lw=0.4,
                             zorder=5, label=f"{n} (n={len(H)})")
    a.set_title("B  Hybrid occurrences", fontsize=9.5, loc='left', fontweight='bold')
    a.legend(loc='lower right', fontsize=6.3, framealpha=0.9)
    a = ax[2]; basemap(a)
    xx, yy = np.mgrid[W:E:200j, S:N:200j]
    zz = gaussian_kde(allh.T, bw_method=0.25)(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
    lm = np.zeros(xx.size, bool)
    for g in (coast_box.geoms if coast_box.geom_type == 'MultiPolygon' else [coast_box]):
        lm |= MP(np.array(g.exterior.coords)).contains_points(np.c_[xx.ravel(), yy.ravel()])
    zz = np.where(lm.reshape(xx.shape), zz, np.nan)
    cf = a.contourf(xx, yy, zz, levels=8, cmap='magma_r', alpha=0.75, zorder=2)
    for n, t, c in PARENTS:
        for r in pr[n]: a.plot([p[0] for p in r], [p[1] for p in r], c=c, lw=0.8, alpha=0.55, zorder=3)
    a.scatter(allh[:, 0], allh[:, 1], s=3, c='k', alpha=0.4, lw=0, zorder=4)
    a.set_title("C  Hybridization hotspots (KDE)", fontsize=9.5, loc='left', fontweight='bold')
    cb = fig.colorbar(cf, ax=a, shrink=0.5, pad=0.02); cb.set_label('rel. hybrid density', fontsize=6.5)
    cb.ax.tick_params(labelsize=6)
    ntot = sum(len(pp[n]) for n, t, c in PARENTS) + len(allh)
    fig.suptitle("Coastal prickly-pear (Opuntia) hybrid complex of cismontane Southern California",
                 fontsize=12.5, fontweight='bold', y=0.99)
    fig.text(0.5, 0.025, f"iNaturalist research-grade observations (n = {ntot:,}; Grubbs-filtered).  "
             f"{pct:.0f}% of hybrid records fall within the O. littoralis – O. oricola sympatry zone.",
             ha='center', fontsize=7.5, color='#444')
    plt.tight_layout(rect=[0, 0.045, 1, 0.965]); plt.savefig(FIGS / "fig_hybrid.png", dpi=160, bbox_inches='tight')
    plt.close(); print("hybrid:", ntot, f"{pct:.0f}% in overlap")


# ---------------------------------------------------------------- PHENOLOGY
def phen_hist(tid, flowering):
    key = f"phen_{tid}_{int(flowering)}"
    if key in cache: return cache[key]
    p = {"taxon_id": tid, "date_field": "observed", "interval": "month_of_year", "quality_grade": "research"}
    if flowering: p.update({"term_id": 12, "term_value_id": 13})
    d = api("https://api.inaturalist.org/v1/observations/histogram?" + urllib.parse.urlencode(p))
    h = {int(k): v for k, v in d["results"]["month_of_year"].items()}
    out = [h.get(m, 0) for m in range(1, 13)]; cache[key] = out; save_cache(); time.sleep(0.6); return out

def fig_phenology():
    months = np.arange(1, 13); mnames = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
    fig = plt.figure(figsize=(12, 5.6), dpi=160)
    axr = fig.add_axes([0.06, 0.10, 0.52, 0.80])
    data = []
    for i, (n, t, c) in enumerate(ALLTAXA):
        fl = phen_hist(t, True); tot = sum(fl)
        series = fl if tot >= 25 else phen_hist(t, False)
        lab_kind = "flowering" if tot >= 25 else "activity"
        arr = np.array(series, float); arr = arr / (arr.max() or 1)
        data.append((n, c, arr, sum(series), lab_kind))
    gap = 1.0
    for i, (n, c, arr, ntot, kind) in enumerate(data):
        base = (len(data) - 1 - i) * gap
        xs = np.linspace(1, 12, 200)
        ys = np.interp(xs, months, arr, period=12)
        axr.fill_between(xs, base, base + ys, color=c, alpha=0.65, lw=0.8, ec='white', zorder=2 + i)
        pk = mnames[int(np.argmax(arr))]
        axr.text(0.2, base + 0.15, f"{n}", fontsize=8, va='bottom', fontstyle='italic')
        axr.text(12.3, base + 0.1, f"n={ntot}\npeak {pk} ({kind})", fontsize=6, va='bottom', color='#555')
    axr.set_xticks(months); axr.set_xticklabels(mnames); axr.set_yticks([])
    axr.set_xlim(0.5, 13.6); axr.set_ylim(-0.2, len(data) * gap + 0.3)
    axr.set_title("A  Flowering phenology by taxon", fontsize=10, loc='left', fontweight='bold')
    axr.set_xlabel("month")
    for s in ['top', 'right', 'left']: axr.spines[s].set_visible(False)

    # rose: whole complex flowering
    axp = fig.add_axes([0.66, 0.12, 0.30, 0.74], projection='polar')
    comp = np.zeros(12)
    for n, t, c in ALLTAXA: comp += np.array(phen_hist(t, True), float)
    theta = (months - 1) / 12 * 2 * np.pi
    width = 2 * np.pi / 12 * 0.9
    axp.bar(theta, comp, width=width, color='#b5651d', alpha=0.8, edgecolor='white', lw=0.6)
    axp.set_theta_zero_location('N'); axp.set_theta_direction(-1)
    axp.set_xticks(theta); axp.set_xticklabels(mnames, fontsize=7)
    axp.set_yticklabels([]); axp.set_title("B  Complex-wide flowering\n(research-grade, n=%d)" % int(comp.sum()),
                                           fontsize=9, fontweight='bold', pad=12)
    fig.suptitle("Flowering phenology of the coastal Opuntia complex (iNaturalist photo annotations)",
                 fontsize=12, fontweight='bold', y=0.99)
    plt.savefig(FIGS / "fig_phenology.png", dpi=160, bbox_inches='tight'); plt.close()
    print("phenology done")


# ---------------------------------------------------------------- EFFORT
def fetch_bg():
    if "bg" in cache: return np.array(cache["bg"])
    pts, id_above = [], 0
    while len(pts) < 9000:
        u = ("https://api.inaturalist.org/v1/observations?taxon_id=%d&quality_grade=research&geo=true"
             "&nelat=%f&nelng=%f&swlat=%f&swlng=%f&per_page=200&order_by=id&order=asc&id_above=%d"
             % (OPUNTIA_GENUS, N, E, S, W, id_above))
        r = api(u); res = r.get("results", [])
        if not res: break
        for o in res:
            loc = o.get("location")
            if loc:
                la, lo = loc.split(","); pts.append([float(lo), float(la)])
        id_above = res[-1]["id"]; time.sleep(0.7)
    cache["bg"] = pts; save_cache(); return np.array(pts)

def fig_effort():
    bg = fetch_bg()
    focal = np.vstack([taxon_pts(t) for n, t, c in ALLTAXA])
    res = 0.1
    xe = np.arange(W, E + res + 1e-9, res)      # cell edges
    ye = np.arange(S, N + res + 1e-9, res)
    def grid(pp):
        H, _, _ = np.histogram2d(pp[:, 0], pp[:, 1], bins=[xe, ye]); return H
    Hf, Hb = grid(focal), grid(bg)
    prop = np.full_like(Hf, np.nan, float)
    mask = Hb >= 4
    prop[mask] = Hf[mask] / Hb[mask]
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.2), dpi=160)
    a = ax[0]; basemap(a)
    a.scatter(bg[:, 0], bg[:, 1], s=2, c='#999', alpha=0.25, lw=0, zorder=2, label=f"all Opuntia (n={len(bg):,})")
    a.scatter(focal[:, 0], focal[:, 1], s=3, c='#c0392b', alpha=0.4, lw=0, zorder=3,
              label=f"coastal complex (n={len(focal):,})")
    a.set_title("A  Raw observations & sampling effort", fontsize=9.5, loc='left', fontweight='bold')
    a.legend(loc='lower right', fontsize=6.5, framealpha=0.9); scalebar(a)
    a = ax[1]; basemap(a)
    pm = np.ma.masked_invalid(prop.T)
    im = a.pcolormesh(xe, ye, pm, cmap='RdYlBu_r', vmin=0, vmax=1, alpha=0.8, zorder=2)
    a.set_title("B  Effort-corrected relative occurrence", fontsize=9.5, loc='left', fontweight='bold')
    cb = fig.colorbar(im, ax=a, shrink=0.6, pad=0.02)
    cb.set_label('fraction of prickly-pear records\nthat are the coastal complex', fontsize=6.5)
    cb.ax.tick_params(labelsize=6)
    fig.suptitle("Effort-corrected occurrence of the coastal Opuntia complex (target-group background)",
                 fontsize=12, fontweight='bold', y=0.99)
    fig.text(0.5, 0.02, "Each cell = focal records ÷ all-Opuntia records (cells with ≥4 background obs). "
             "Corrects for where people look, not just where they go.", ha='center', fontsize=7.5, color='#444')
    plt.tight_layout(rect=[0, 0.04, 1, 0.96]); plt.savefig(FIGS / "fig_effort.png", dpi=160, bbox_inches='tight')
    plt.close(); print("effort: focal", len(focal), "bg", len(bg))


# ---------------------------------------------------------------- NICHE
def get_elev(pts):
    out = {}
    todo = []
    for x, y in pts:
        k = f"{round(x,3)},{round(y,3)}"
        if k in cache.get("elev", {}): out[k] = cache["elev"][k]
        else: todo.append((x, y, k))
    cache.setdefault("elev", {})
    for i in range(0, len(todo), 100):
        chunk = todo[i:i + 100]
        lat = ",".join(str(round(y, 4)) for x, y, k in chunk)
        lon = ",".join(str(round(x, 4)) for x, y, k in chunk)
        r = api(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}")
        for (x, y, k), e in zip(chunk, r["elevation"]):
            cache["elev"][k] = e; out[k] = e
        save_cache(); time.sleep(2.0)
    return out

def fig_niche():
    cl = np.cos(np.radians((S + N) / 2))
    # Ocean = generous box minus land (only the Pacific lies within it), so
    # distance-to-ocean = true distance-to-coast with no artificial bbox edges.
    ocean = box(-122, 31, -110, 37).difference(land)
    ocean_t = shapely.ops.transform(lambda a, b: (a * cl, b), ocean)
    def dc(x, y): return Point(x * cl, y).distance(ocean_t) * 111
    samples = {}
    for n, t, c in ALLTAXA:
        P = taxon_pts(t)
        if len(P) > 180:
            P = P[np.random.RandomState(0).choice(len(P), 180, replace=False)]
        samples[n] = P
    allpts = [tuple(p) for P in samples.values() for p in P]
    elev = get_elev(allpts)
    rows = {}
    for n, t, c in ALLTAXA:
        P = samples[n]
        d = np.array([dc(x, y) for x, y in P])
        e = np.array([elev[f"{round(x,3)},{round(y,3)}"] for x, y in P])
        rows[n] = (d, e, c)
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 5), dpi=160)
    a = ax[0]
    for n, t, c in ALLTAXA:
        d, e, _ = rows[n]
        a.scatter(d, e, s=10, c=c, alpha=0.40, lw=0, label=n)
        if len(d) > 5:   # axis-aligned 1-SD ellipse (axes have different units)
            a.add_patch(Ellipse((np.median(d), np.median(e)), 2 * d.std(), 2 * e.std(),
                                angle=0, fc='none', ec=c, lw=1.6, alpha=0.95))
    a.set_xlabel("distance to coast (km) — marine / fog influence")
    a.set_ylabel("elevation (m)")
    a.set_title("A  Coastal environmental niche", fontsize=9.5, loc='left', fontweight='bold')
    a.set_xlim(-3, np.percentile(np.concatenate([rows[n][0] for n in [x[0] for x in ALLTAXA]]), 97))
    a.set_ylim(-30, np.percentile(np.concatenate([rows[n][1] for n in [x[0] for x in ALLTAXA]]), 97))
    a.legend(fontsize=6.3, framealpha=0.9, loc='upper right'); a.grid(alpha=0.2)

    # Schoener's D in 2D
    names = [n for n, t, c in ALLTAXA]
    dall = np.concatenate([rows[n][0] for n in names]); eall = np.concatenate([rows[n][1] for n in names])
    dbin = np.linspace(0, np.percentile(dall, 98), 12); ebin = np.linspace(0, np.percentile(eall, 98), 12)
    def occ(n):
        d, e, _ = rows[n]
        Hh, _, _ = np.histogram2d(d, e, bins=[dbin, ebin]); Hh = Hh / (Hh.sum() or 1); return Hh
    O = {n: occ(n) for n in names}
    D = np.zeros((6, 6))
    for i, ni in enumerate(names):
        for j, nj in enumerate(names):
            D[i, j] = 1 - 0.5 * np.abs(O[ni] - O[nj]).sum()
    a = ax[1]
    im = a.imshow(D, cmap='YlGnBu', vmin=0, vmax=1)
    short = [n.replace("Opuntia ", "O. ").replace("× ", "×") for n in names]
    a.set_xticks(range(6)); a.set_yticks(range(6))
    a.set_xticklabels(short, rotation=45, ha='right', fontsize=6.5, fontstyle='italic')
    a.set_yticklabels(short, fontsize=6.5, fontstyle='italic')
    for i in range(6):
        for j in range(6):
            a.text(j, i, f"{D[i,j]:.2f}", ha='center', va='center', fontsize=6,
                   color='white' if D[i, j] > 0.5 else '#222')
    a.set_title("B  Niche overlap (Schoener's D)", fontsize=9.5, loc='left', fontweight='bold')
    cb = fig.colorbar(im, ax=a, shrink=0.7, pad=0.02); cb.set_label("D", fontsize=7)
    fig.suptitle("Environmental niche of the coastal Opuntia complex (distance-to-coast × elevation)",
                 fontsize=12, fontweight='bold', y=0.99)
    fig.text(0.5, 0.02, "Elevation: Open-Meteo DEM. Distance-to-coast from Natural Earth shoreline. "
             "Ellipses = 1 SD. Schoener's D: 0 = no overlap, 1 = identical niche.", ha='center',
             fontsize=7.5, color='#444')
    plt.tight_layout(rect=[0, 0.04, 1, 0.96]); plt.savefig(FIGS / "fig_niche.png", dpi=160, bbox_inches='tight')
    plt.close(); print("niche done")


if __name__ == "__main__":
    import shapely.ops
    fig_hybrid()
    fig_phenology()
    fig_effort()
    fig_niche()
    print("ALL FIGURES ->", FIGS)
