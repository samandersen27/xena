"""
Xena — species richness grid

Counts how many native range polygons overlap each point on a grid across
the US Southwest (just the SW states), producing a "how many species occupy
this area" field for a contour/heat layer.

Reads:  frontend/public/ranges.json, frontend/public/sw_states.json
Writes: frontend/public/richness.json
"""

import json
from pathlib import Path as FsPath

import numpy as np
from matplotlib.path import Path as MplPath

HERE   = FsPath(__file__).parent / "frontend" / "public"
RANGES = HERE / "ranges.json"
STATES = HERE / "sw_states.json"
OUT    = HERE / "richness.json"

# SW window (lng/lat). The state mask trims everything outside the SW states.
WEST, EAST, SOUTH, NORTH = -125.0, -93.0, 25.0, 43.0
RES = 0.1   # ~11 km cells


def main():
    ranges = json.loads(RANGES.read_text(encoding="utf-8"))["ranges"]
    states = json.loads(STATES.read_text(encoding="utf-8"))

    xs = np.arange(WEST, EAST + RES, RES)
    ys = np.arange(SOUTH, NORTH + RES, RES)
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys)
    pts = np.column_stack([X.ravel(), Y.ravel()])

    # Species richness: how many range polygons contain each grid point
    counts = np.zeros(pts.shape[0], dtype=np.int32)
    for r in ranges.values():
        inside = np.zeros(pts.shape[0], dtype=bool)
        for ring in r.get("polygons") or [r.get("polygon")]:
            if ring and len(ring) >= 4:
                inside |= MplPath(ring).contains_points(pts)
        counts += inside

    # Mask to the SW states only
    inside = np.zeros(pts.shape[0], dtype=bool)
    for s in states:
        for ring in s.get("rings", []):
            if len(ring) >= 4:
                inside |= MplPath(ring).contains_points(pts)

    counts[~inside] = -1   # -1 => outside SW (rendered transparent)
    grid = counts.reshape(ny, nx)

    OUT.write_text(json.dumps({
        "res":  RES,
        "bbox": [WEST, SOUTH, EAST, NORTH],
        "nx":   nx,
        "ny":   ny,
        "max":  int(counts.max()),
        # row-major, south->north rows (ys ascending), west->east columns
        "data": grid.astype(int).tolist(),
    }), encoding="utf-8")

    inside_vals = counts[inside]
    print(f"grid {nx}x{ny} | SW cells {inside.sum()} | "
          f"richness max {counts.max()} | mean(in-SW) {inside_vals.mean():.1f}")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
