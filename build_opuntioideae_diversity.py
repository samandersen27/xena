"""
Opuntioideae diversity = Opuntia (prickly pears) + Cylindropuntia/Grusonia
(chollas) overlaid into one subfamily-level richness map. Pure recomputation
from the existing refined ranges — no iNaturalist calls.

Reads:  frontend/public/opuntia_ranges.json, cholla_ranges.json, sw_states.json
Writes: frontend/public/opuntioideae_richness.json
"""
import json
from pathlib import Path
import numpy as np
from matplotlib.path import Path as MplPath

PUB = Path(__file__).parent / "frontend" / "public"
WEST, EAST, SOUTH, NORTH = -125.0, -93.0, 25.0, 43.0
RES = 0.1


def main():
    op = json.loads((PUB / "opuntia_ranges.json").read_text())["ranges"]
    ch = json.loads((PUB / "cholla_ranges.json").read_text())["ranges"]
    ranges = {**op, **ch}                      # different taxa — no key collisions
    print(f"Opuntia {len(op)} + chollas {len(ch)} = {len(ranges)} Opuntioideae taxa")

    states = json.loads((PUB / "sw_states.json").read_text())
    xs = np.arange(WEST, EAST + RES, RES); ys = np.arange(SOUTH, NORTH + RES, RES)
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys); pts = np.column_stack([X.ravel(), Y.ravel()])

    counts = np.zeros(pts.shape[0], dtype=np.int32)
    for r in ranges.values():
        inside = np.zeros(pts.shape[0], dtype=bool)
        for ring in (r.get("polygons") or [r.get("polygon")]):
            if ring and len(ring) >= 4:
                inside |= MplPath(ring).contains_points(pts)
        counts += inside

    sw = np.zeros(pts.shape[0], bool)
    for st in states:
        for ring in st.get("rings", []):
            if len(ring) >= 4:
                sw |= MplPath(ring).contains_points(pts)
    counts[~sw] = -1
    grid = counts.reshape(ny, nx)

    out = PUB / "opuntioideae_richness.json"
    out.write_text(json.dumps({
        "res": RES, "bbox": [WEST, SOUTH, EAST, NORTH], "nx": nx, "ny": ny,
        "max": int(counts.max()), "data": grid.astype(int).tolist()}), encoding="utf-8")
    print(f"richness: {nx}x{ny}, max {counts.max()} overlapping Opuntioideae -> {out.name}")


if __name__ == "__main__":
    main()
