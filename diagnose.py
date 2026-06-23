"""
Xena — iNaturalist diagnostic
Prints raw taxon data for your first 20 observations so we can
see exactly what the API is returning and why genus detection is failing.

Run with: python diagnose.py
"""

import json
import urllib.request
import urllib.parse
from collections import defaultdict

USERNAME = "samandersen"
TAXON_ID = 47902
HEADERS  = {"User-Agent": "Xena-CactusMuseum/0.1"}


def fetch_page(page=1, per_page=100):
    params = {
        "user_login": USERNAME,
        "taxon_id":   TAXON_ID,
        "per_page":   per_page,
        "page":       page,
        "order_by":   "observed_on",
        "order":      "desc",
    }
    url = "https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    print(f"\n🌵 Xena diagnostic — {USERNAME}\n")

    data  = fetch_page(per_page=50)
    total = data["total_results"]
    print(f"Total cactus observations on iNat: {total}\n")
    print("=" * 60)

    name_counts = defaultdict(int)
    rank_counts = defaultdict(int)

    for obs in data["results"]:
        t = obs.get("taxon") or {}
        tid      = t.get("id")
        name     = t.get("name", "MISSING")
        rank     = t.get("rank", "MISSING")
        common   = t.get("preferred_common_name", "")
        ancestors = t.get("ancestors", [])
        # Check what's actually in the taxon object
        taxon_keys = list(t.keys()) if t else []

        name_counts[name] += 1
        rank_counts[rank] += 1

        print(f"  obs {obs['id']:>10}  |  {name:<35}  rank={rank:<12}  common={common}")
        print(f"               taxon keys: {taxon_keys}")
        if ancestors:
            print(f"               ancestors: {[(a.get('rank'), a.get('name')) for a in ancestors]}")
        else:
            print(f"               ancestors: (none in response)")
        print()

    print("=" * 60)
    print("\n=== UNIQUE TAXON NAMES IN THESE 50 OBS ===")
    for name, count in sorted(name_counts.items()):
        print(f"  {count:>3}x  {name}")

    print("\n=== RANK BREAKDOWN ===")
    for rank, count in sorted(rank_counts.items(), key=lambda x: -x[1]):
        print(f"  {count:>3}x  {rank}")

    # Now try fetching one taxon directly from /taxa to compare
    # Pick the first non-Opuntia taxon if there is one
    sample_taxon = None
    for obs in data["results"]:
        t = obs.get("taxon") or {}
        if t.get("name", "").split()[0] != "Opuntia":
            sample_taxon = t
            break
    if not sample_taxon:
        sample_taxon = (data["results"][0].get("taxon") or {})

    if sample_taxon.get("id"):
        print(f"\n=== DIRECT /taxa LOOKUP for '{sample_taxon.get('name')}' (id={sample_taxon['id']}) ===")
        url = f"https://api.inaturalist.org/v1/taxa/{sample_taxon['id']}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            tdata = json.loads(resp.read())
        if tdata.get("results"):
            t2 = tdata["results"][0]
            print(f"  name:       {t2.get('name')}")
            print(f"  rank:       {t2.get('rank')}")
            print(f"  ancestors:  {[(a.get('rank'), a.get('name')) for a in t2.get('ancestors', [])]}")
            print(f"  all keys:   {list(t2.keys())}")

    print("\n✓ Done.\n")


if __name__ == "__main__":
    main()
