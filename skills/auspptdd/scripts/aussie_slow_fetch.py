#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aussie_slow_fetch.py — property facts from Aussie property pages (Cotality data; free, slow, rate-limited).

Per page it returns:
  text facts   beds, baths, floor area, land area, year built, storeys, plus the "Property history" lines (listed / sold / rental);
  JSON-LD      date_posted (RealEstateListing.datePosted), agency (the agency name only - no agent names or contacts), geo {lat, lon},
               images [urls], description (the FULL RealEstateListing.description: it often carries levies, sizes on title,
               "Approximate Outgoings", etc.), plus ld_beds / ld_baths / ld_floor_m2 / ld_built as a cross-check of the text facts.
land_m2 for a UNIT is the strata lot area (title area, often internal + balcony + parking + storage), NOT a land holding; the output
carries land_note saying so. Never use it for land-value-per-m2 maths on a unit.

Rate limit: the site returns 202 (empty) when throttled: one page per ~75 s, up to three attempts each. After 2 consecutive HTTP 202
responses the script stops early (writes what it has) and prints "rate-limited: Aussie blocks batch fetching of the same building -
use the Domain building profile for same-building sales". For a whole building use domain_building_profile.js instead; this script is
for a handful of single pages (subject, a few comps). 18 pages take about 45 minutes - run in the background.
Slugs: suburb "salamander-bay-2317", address "112a-salamander-way" (street type in full, lower case).

usage:
  python aussie_slow_fetch.py --suburb salamander-bay-2317 --slugs 112a-salamander-way 136-salamander-way [--state nsw] [--out aussie_attrs.json] [--sleep 75] [--max-202 2]
  python aussie_slow_fetch.py --suburb salamander-bay-2317 --slug-file slugs.txt
"""
import re, sys, json, time, argparse, urllib.request
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36", "Accept-Language": "en-AU,en;q=0.9", "Accept": "text/html"}
RATE_MSG = "rate-limited: Aussie blocks batch fetching of the same building — use the Domain building profile for same-building sales"
LAND_NOTE = "land_m2 for a unit is the strata lot area (title area incl. balcony/parking/storage), not a land holding"
def fetch(state, sub, slug):
    try:
        r = urllib.request.urlopen(urllib.request.Request("https://www.aussie.com.au/property/%s/%s/%s/" % (state, sub, slug), headers=H), timeout=40)
        return r.status, r.read().decode("utf-8", "replace")
    except Exception as e: return 0, repr(e)[:80]

def ld_nodes(html):
    """All JSON-LD nodes (flattened @graph) in the page."""
    nodes = []
    for b in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try: j = json.loads(b)
        except ValueError: continue
        for n in (j if isinstance(j, list) else [j]):
            if isinstance(n, dict): nodes += n["@graph"] if isinstance(n.get("@graph"), list) else [n]
    return [n for n in nodes if isinstance(n, dict)]

def parse_ld(html):
    d = {}
    for n in ld_nodes(html):
        t = n.get("@type"); t = t[0] if isinstance(t, list) and t else t
        if t == "RealEstateListing":
            d["date_posted"] = n.get("datePosted"); d["description"] = n.get("description")
            if n.get("image"): d.setdefault("_img", []).extend(n["image"] if isinstance(n["image"], list) else [n["image"]])
        elif t == "RealEstateAgent":
            po = n.get("parentOrganization")
            d["agency"] = po.get("name") if isinstance(po, dict) else n.get("name")  # agency only: no individual agent name / phone / email kept
        elif t in ("Apartment", "House", "SingleFamilyResidence", "Residence", "Accommodation", "Place"):
            g = n.get("geo") or {}
            if g.get("latitude") is not None: d["geo"] = {"lat": float(g["latitude"]), "lon": float(g["longitude"])}
            fs = n.get("floorSize") or {}
            d.update({"ld_beds": n.get("numberOfBedrooms"), "ld_baths": n.get("numberOfBathroomsTotal"), "ld_floor_m2": fs.get("value") if isinstance(fs, dict) else None, "ld_built": n.get("yearBuilt")})
            if n.get("image"): d.setdefault("_img", []).extend(n["image"] if isinstance(n["image"], list) else [n["image"]])
    return d

def parse_images(html, extra):
    urls = list(extra)
    urls += re.findall(r'https?://[^"\'\s\\<>)]+?\.(?:jpe?g|png|webp)', html, re.I)
    seen, out = set(), []
    for u in urls:
        if u in seen or "favicon" in u or "logo" in u.lower() or "sprite" in u.lower(): continue
        seen.add(u); out.append(u)
    if extra:  # keep this listing's own photos: same folder as the JSON-LD hero image (the page also carries other listings' thumbnails)
        pre = extra[0].rsplit("/", 2)[0]
        own = [u for u in out if u.startswith(pre)]
        if own: out = own
    return out[:60]

def parse_page(s):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S); t = re.sub(r"<[^>]+>", " ", t); t = re.sub(r"\s+", " ", t)
    g = lambda p: (re.search(p, t) or [None, None])[1]
    d = {"beds": g(r"includes (\d+) bedroom") or g(r"[Tt]his (\d+)-bedroom"), "baths": g(r"(\d+) bathroom"),
         "floor_m2": g(r"(\d+) sqm of floor space") or g(r"internal floor area of around (\d+) square"),
         "land_m2": g(r"land size of approximately ([\d,]+) square"), "built": g(r"built in (\d{4})"),
         "storeys": g(r"house: ([a-z /]+?) Property Description")}
    d["land_note"] = LAND_NOTE
    d["history"] = re.findall(r"((?:Listed for sale|Sold|Rental|Listed for rent)[^.]{0,60}?(?:\$[\d,]+(?:/week|/wk|pw)?|[A-Z][a-z]{2} \d{4}))", t)[:12]
    # event + price pairs, e.g. "Listed for sale Jun 2026 For Sale @ $1,350,000" / "Sold Feb 2019 ... $785,000" / "Rental Jul 2026 $995/week"
    d["history_priced"] = [{"event": e.strip(), "price": pr} for e, pr in re.findall(r"((?:Listed for sale|Sold|Rental|Listed for rent)\s+[A-Z][a-z]{2} \d{4})[^$]{0,40}?(\$[\d,]+(?:/week|/wk|pw)?)", t)][:12]
    j = t.find("How many bedrooms"); d["faq"] = t[j:j + 230] if j > 0 else ""
    ld = parse_ld(s); img = ld.pop("_img", []); d.update(ld); d["images"] = parse_images(s, img)
    return d

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suburb", required=True); ap.add_argument("--slugs", nargs="*", default=[]); ap.add_argument("--slug-file")
    ap.add_argument("--state", default="nsw"); ap.add_argument("--out", default="aussie_attrs.json"); ap.add_argument("--sleep", type=int, default=75)
    ap.add_argument("--max-202", type=int, default=2, help="stop early after this many consecutive HTTP 202 responses (default 2)")
    ap.add_argument("--from-html", help="parse a saved Aussie page (offline test / re-parse) and print the result, no network")
    a = ap.parse_args(); slugs = list(a.slugs)
    if a.from_html:
        d = parse_page(open(a.from_html, encoding="utf-8", errors="replace").read())
        json.dump({"offline": d}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print(json.dumps(d, ensure_ascii=False)[:600]); print("written", a.out); return
    if a.slug_file: slugs += [l.strip() for l in open(a.slug_file, encoding="utf-8") if l.strip()]
    out = {}; consec = 0; stopped = False
    for i, slug in enumerate(slugs):
        d = {"status": None}; s = ""
        for attempt in range(3):
            st, s = fetch(a.state, a.suburb, slug); d["status"] = st
            consec = consec + 1 if st == 202 else 0
            if st == 200 and len(s) > 50000: break
            if consec >= a.max_202: break
            time.sleep(90)
        if d["status"] == 200 and len(s) > 50000: d.update(parse_page(s))
        out[slug] = d; print(slug, json.dumps(d, ensure_ascii=False)[:300], flush=True)
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if consec >= a.max_202:
            print(RATE_MSG); stopped = True; break
        if i < len(slugs) - 1: time.sleep(a.sleep)
    print("written", a.out, "(stopped early: rate-limited)" if stopped else "")
    print("NOTE:", LAND_NOTE)
if __name__ == "__main__":
    main()
