"""
Xena — iNaturalist sync
Pulls all your cactus observations and writes them to frontend/public/data.json
The React app reads this file directly — no database or backend needed.

Run with: python sync.py
Requires: Python 3.7+, no third-party packages
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
USERNAME       = "samandersen"
TAXON_ID       = 47903          # Cactaceae family
PER_PAGE       = 200
OUTPUT_PATH    = Path(__file__).parent / "frontend" / "public" / "data.json"
CHECKLIST_PATH = Path(__file__).parent / "xena_southwest_checklist.txt"   # raw source (reference)
NATIVES_PATH   = Path(__file__).parent / "natives.csv"                    # refined native checklist
HEADERS        = {"User-Agent": "Xena-CactusMuseum/0.1"}

PHOTO_SIZES = ("square", "small", "medium", "large", "original")


# ── Load master checklist ─────────────────────────────────────────────────────

def load_checklist() -> list:
    """
    Load the refined native checklist from natives.csv — the deduplicated,
    iNaturalist-aligned list of US Southwest natives. This is the source of
    truth for the progress denominator and the species tiles:
      - deduplicated (synonyms collapsed to one iNat-active name)
      - non-natives are excluded by construction (anything not on this list)
      - each row carries its resolved iNat taxon ID for range/observation matching

    Returns list of {name, common_name, genus, inat_id} dicts.
    """
    import csv

    if not NATIVES_PATH.exists():
        print(f"  ⚠ natives.csv not found at {NATIVES_PATH}")
        return []

    checklist = []
    with open(NATIVES_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("Botanical name") or "").strip()
            if not name:
                continue
            id_raw = (row.get("iNat ID") or "").strip()
            checklist.append({
                "name":        name,
                "common_name": (row.get("Common name") or "").strip(),
                "genus":       (row.get("Genus") or name.split()[0]).strip(),
                "inat_id":     int(id_raw) if id_raw.isdigit() else None,
            })

    return checklist


# ── Helpers ───────────────────────────────────────────────────────────────────

def photo_url(raw: str, size: str) -> str:
    for s in PHOTO_SIZES:
        if f"/{s}." in raw:
            return raw.replace(f"/{s}.", f"/{size}.")
    return raw


def parse_location(loc: str):
    if not loc:
        return None, None
    try:
        lat, lng = loc.split(",")
        return float(lat.strip()), float(lng.strip())
    except Exception:
        return None, None


def extract_state(place_guess: str, lat: float = None, lng: float = None) -> str:
    """
    Determine US state from coordinates first (reliable), falling back
    to text matching on place_guess only if coordinates are unavailable.

    Text matching alone is fragile: iNat place_guess strings often use
    two-letter abbreviations ("Zion NP, UT") rather than full names, and
    a string like "Arizona Strip, UT" would match on "Arizona" even
    though the observation is actually in Utah. Coordinates avoid both
    problems entirely.
    """
    # Rough bounding boxes for southwestern US states (lat_min, lat_max, lng_min, lng_max)
    # Boxes intentionally a bit generous since they're just for state tagging,
    # not GIS-precision tasks. Order matters where boxes overlap — more specific
    # states checked first.
    STATE_BOUNDS = [
        ("Arizona",    31.3, 37.0, -114.9, -109.0),
        ("California", 32.5, 42.0, -124.5, -114.1),
        ("Nevada",     35.0, 42.0, -120.0, -114.0),
        ("Utah",       37.0, 42.0, -114.1, -109.0),
        ("New Mexico", 31.3, 37.0, -109.1, -103.0),
        ("Colorado",   37.0, 41.0, -109.1, -102.0),
        ("Texas",      25.8, 36.5, -106.7, -93.5),
        ("Oregon",     42.0, 46.3, -124.6, -116.5),
        ("Idaho",      42.0, 49.0, -117.3, -111.0),
        ("Wyoming",    41.0, 45.0, -111.1, -104.0),
        ("Montana",    44.4, 49.0, -116.1, -104.0),
        ("Washington", 45.5, 49.0, -124.8, -116.9),
    ]

    if lat is not None and lng is not None:
        for state, lat_min, lat_max, lng_min, lng_max in STATE_BOUNDS:
            if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
                return state

    if not place_guess:
        return None

    # Fallback: text match, including common abbreviations
    full_names = {
        "Arizona": ["Arizona", ", AZ"],
        "California": ["California", ", CA"],
        "Nevada": ["Nevada", ", NV"],
        "Utah": ["Utah", ", UT"],
        "New Mexico": ["New Mexico", ", NM"],
        "Colorado": ["Colorado", ", CO"],
        "Texas": ["Texas", ", TX"],
        "Oregon": ["Oregon", ", OR"],
        "Idaho": ["Idaho", ", ID"],
        "Wyoming": ["Wyoming", ", WY"],
        "Montana": ["Montana", ", MT"],
        "Washington": ["Washington", ", WA"],
        "Baja California": ["Baja California"],
    }
    for state, patterns in full_names.items():
        if any(p in place_guess for p in patterns):
            return state
    return None


def get_genus(taxon: dict) -> str:
    if not taxon:
        return "Unknown"
    rank = taxon.get("rank", "")
    name = taxon.get("name", "")
    if rank == "genus":
        return name
    for ancestor in taxon.get("ancestors", []):
        if ancestor.get("rank") == "genus":
            return ancestor["name"]
    parts = name.strip().split()
    if len(parts) >= 2:
        return parts[0]
    return name or "Unknown"


def fetch_taxon_details(inat_taxon_id: int) -> dict:
    url = f"https://api.inaturalist.org/v1/taxa/{inat_taxon_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            results = data.get("results", [])
            return results[0] if results else {}
    except Exception:
        return {}


def fetch_page(page: int) -> dict:
    params = {
        "user_login": USERNAME,
        "taxon_id":   TAXON_ID,
        "per_page":   PER_PAGE,
        "page":       page,
        "order_by":   "observed_on",
        "order":      "desc",
    }
    url = "https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🌵 Xena sync — {USERNAME}")
    print(f"   Output: {OUTPUT_PATH}\n")

    # Load refined native checklist (natives.csv)
    checklist = load_checklist()
    total_sw_species = len(checklist)
    checklist_names  = {c["name"].lower() for c in checklist}
    checklist_ids    = {c["inat_id"] for c in checklist if c.get("inat_id")}
    print(f"  Checklist loaded: {total_sw_species} native Southwest species\n")

    # Build per-genus totals from checklist
    checklist_by_genus = defaultdict(list)
    for c in checklist:
        checklist_by_genus[c["genus"]].append(c)

    # Fetch all pages
    print("Fetching page 1...")
    first       = fetch_page(1)
    total       = first["total_results"]
    total_pages = -(-total // PER_PAGE)
    print(f"   {total} observations across {total_pages} page(s)\n")

    raw_obs = list(first["results"])
    for page in range(2, total_pages + 1):
        print(f"Fetching page {page}/{total_pages}...")
        time.sleep(1.1)
        raw_obs.extend(fetch_page(page)["results"])

    print(f"\n✓ Fetched {len(raw_obs)} observations")

    # ── Transform observations ────────────────────────────────────────────────
    observations = []
    taxa_map     = {}

    taxon_raw = {}
    for raw in raw_obs:
        t = raw.get("taxon") or {}
        tid = t.get("id")
        if tid and tid not in taxon_raw:
            taxon_raw[tid] = t

    needs_lookup = []
    for tid, t in taxon_raw.items():
        genus = get_genus(t)
        if genus in ("Unknown", "Cactaceae") or (
            t.get("rank") not in ("species","subspecies","variety","genus")
            and len((t.get("name","")).split()) < 2
        ):
            needs_lookup.append(tid)

    if needs_lookup:
        print(f"\nFetching full taxon details for {len(needs_lookup)} ambiguous taxa...")
        for i, tid in enumerate(needs_lookup):
            if i > 0:
                time.sleep(0.5)
            details = fetch_taxon_details(tid)
            if details:
                taxon_raw[tid] = details
                genus = get_genus(details)
                print(f"  {details.get('name','?')} → genus: {genus}")

    for tid, t in taxon_raw.items():
        genus = get_genus(t)
        taxa_map[tid] = {
            "inat_id":     tid,
            "rank":        t.get("rank"),
            "name":        t.get("name"),
            "genus":       genus,
            "common_name": t.get("preferred_common_name"),
            "inat_url":    f"https://www.inaturalist.org/taxa/{tid}",
        }

    for raw in raw_obs:
        taxon    = raw.get("taxon") or {}
        inat_tid = taxon.get("id")
        lat, lng = parse_location(raw.get("location"))
        photos   = raw.get("photos") or []

        obs = {
            "id":                    raw["id"],
            "inat_url":              f"https://www.inaturalist.org/observations/{raw['id']}",
            "observed_on":           raw.get("observed_on"),
            "quality_grade":         raw.get("quality_grade"),
            "obscured":              raw.get("obscured", False),
            "latitude":              lat,
            "longitude":             lng,
            "place_guess":           raw.get("place_guess"),
            "state":                 extract_state(raw.get("place_guess"), lat, lng),
            "description":           raw.get("description"),
            "comments_count":        raw.get("comments_count", 0),
            "identifications_count": raw.get("identifications_count", 0),
            "taxon_inat_id":         inat_tid,
            "photos": [
                {
                    "id":          p.get("id"),
                    "square":      photo_url(p["url"], "square"),
                    "small":       photo_url(p["url"], "small"),
                    "medium":      photo_url(p["url"], "medium"),
                    "large":       photo_url(p["url"], "large"),
                    "original":    photo_url(p["url"], "original"),
                    "license":     p.get("license_code"),
                    "attribution": p.get("attribution"),
                }
                for p in photos if p.get("url")
            ],
        }
        observations.append(obs)

    taxa = list(taxa_map.values())

    # Print genus breakdown
    genus_counts = defaultdict(int)
    for t in taxa:
        genus_counts[t["genus"]] += 1
    print("\n=== GENERA FOUND ===")
    for genus, count in sorted(genus_counts.items()):
        print(f"  {genus:30s} {count} species")

    # ── Compute summary stats ─────────────────────────────────────────────────
    species_obs = defaultdict(list)
    for obs in observations:
        if obs["taxon_inat_id"]:
            species_obs[obs["taxon_inat_id"]].append(obs)

    # Cross-reference observed species against the native checklist.
    # A checklist species counts as observed if Sam has a real observation
    # whose taxon matches it by iNat ID or by name (covers genus-renamed taxa).
    observed_ids = {
        t["inat_id"] for t in taxa
        if t.get("inat_id") and len(species_obs.get(t["inat_id"], [])) > 0
    }
    observed_names = {
        t["name"].lower() for t in taxa
        if t.get("rank") == "species" and len(species_obs.get(t["inat_id"], [])) > 0
    }
    matched = [
        c for c in checklist
        if (c.get("inat_id") and c["inat_id"] in observed_ids)
        or c["name"].lower() in observed_names
    ]
    n_matched = len(matched)
    checklist_observed = {c["name"].lower() for c in matched}      # back-compat
    checklist_remaining = checklist_names - checklist_observed

    # Per-genus progress using checklist as denominator
    genus_map = defaultdict(lambda: {
        "species_ids": set(), "obs_count": 0, "last_seen": None,
        "checklist_total": 0,
    })
    # Seed with checklist totals
    for genus, items in checklist_by_genus.items():
        genus_map[genus]["checklist_total"] = len(items)

    for taxon in taxa:
        g = taxon["genus"]
        obs_list = species_obs.get(taxon["inat_id"], [])
        # Only count this taxon as "observed" if it has at least one
        # actual observation — taxa can exist in `taxa` with zero
        # observations if they came from a fallback /taxa lookup or
        # were only ever identified at genus rank.
        if obs_list:
            genus_map[g]["species_ids"].add(taxon["inat_id"])
        genus_map[g]["obs_count"] += len(obs_list)
        dates = [o["observed_on"] for o in obs_list if o["observed_on"]]
        if dates:
            latest = max(dates)
            if genus_map[g]["last_seen"] is None or latest > genus_map[g]["last_seen"]:
                genus_map[g]["last_seen"] = latest

    genera = [
        {
            "genus":            g,
            "species_observed": len(info["species_ids"]),
            "checklist_total":  info["checklist_total"],
            "obs_count":        info["obs_count"],
            "last_seen":        info["last_seen"],
        }
        for g, info in sorted(genus_map.items())
    ]

    # Overall progress
    # unique_species: distinct species-rank taxa that have at least one
    # actual observation — NOT just every taxon that ended up in taxa_map
    # (which can include genus-level IDs or taxa pulled in via the
    # fallback /taxa lookup with zero observations attached).
    unique_species  = sum(
        1 for t in taxa
        if t.get("rank") == "species" and len(species_obs.get(t["inat_id"], [])) > 0
    )
    total_obs       = len(observations)
    states_visited  = len({o["state"] for o in observations if o["state"]})
    field_days      = len({o["observed_on"] for o in observations if o["observed_on"]})
    research_grade  = sum(1 for o in observations if o["quality_grade"] == "research")
    dates           = sorted(o["observed_on"] for o in observations if o["observed_on"])

    progress = {
        "species_observed":      unique_species,
        "checklist_total":       total_sw_species,        # refined native list — the real denominator
        "checklist_matched":     n_matched,               # native checklist species you've observed
        "checklist_remaining":   total_sw_species - n_matched,
        "pct_complete":          round(n_matched / total_sw_species * 100, 1) if total_sw_species else 0,
        "total_observations":    total_obs,
        "research_grade":        research_grade,
        "field_days":            field_days,
        "states_visited":        states_visited,
        "genera_count":          len(genera),
        "earliest":              dates[0]  if dates else None,
        "latest":                dates[-1] if dates else None,
    }

    # Best photo per species
    species_best_photo = {}
    for tid, obs_list in species_obs.items():
        rg   = [o for o in obs_list if o["quality_grade"] == "research" and o["photos"]]
        any_ = [o for o in obs_list if o["photos"]]
        best = rg or any_
        if best:
            best.sort(key=lambda o: o["observed_on"] or "", reverse=True)
            species_best_photo[tid] = best[0]["photos"][0]["medium"]

    for t in taxa:
        t["best_photo"]      = species_best_photo.get(t["inat_id"])
        t["obs_count"]       = len(species_obs.get(t["inat_id"], []))
        t["on_checklist"]    = t.get("name", "").lower() in checklist_names
        t["last_seen"]       = max(
            (o["observed_on"] for o in species_obs.get(t["inat_id"], []) if o["observed_on"]),
            default=None,
        )

    # ── Write output ──────────────────────────────────────────────────────────
    output = {
        "synced_at":    datetime.utcnow().isoformat() + "Z",
        "progress":     progress,
        "genera":       genera,
        "taxa":         taxa,
        "observations": observations,
        "checklist":    checklist,   # refined native list (name, common, genus, inat_id)
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # Publish the native checklist so it's downloadable from the site
    if NATIVES_PATH.exists():
        import shutil
        shutil.copy(NATIVES_PATH, OUTPUT_PATH.parent / "natives.csv")

    # Optional site background: drop a background.tif (or .tiff/.jpg/.png) in the
    # repo root or frontend/public and it becomes the page backdrop. TIFF isn't
    # web-renderable, so convert it to a web JPEG the CSS references.
    HERE = Path(__file__).parent
    for cand in ("background.tif", "background.tiff", "background.jpg", "background.png"):
        for base in (HERE, OUTPUT_PATH.parent):
            src = base / cand
            if src.exists():
                try:
                    from PIL import Image
                    im = Image.open(src).convert("RGB")
                    im.thumbnail((2400, 2400))
                    im.save(OUTPUT_PATH.parent / "background.jpg", quality=85)
                    print(f"  Background            : {src.name} -> background.jpg")
                except Exception as e:
                    print(f"  Background            : could not convert {src.name} ({e})")
                break
        else:
            continue
        break

    print(f"\n=== SUMMARY ===")
    print(f"  Total observations   : {total_obs}")
    print(f"  Species on iNat      : {unique_species}")
    print(f"  Checklist total      : {total_sw_species}")
    print(f"  Checklist matched    : {len(checklist_observed)}")
    print(f"  Progress             : {progress['pct_complete']}%")
    print(f"  Research grade       : {research_grade}")
    print(f"  Field days           : {field_days}")
    print(f"  States               : {states_visited}")
    print(f"  Output               : {OUTPUT_PATH}")
    print(f"\n✓ Done. Run `npm run dev` in /frontend to see it live.\n")


if __name__ == "__main__":
    main()
