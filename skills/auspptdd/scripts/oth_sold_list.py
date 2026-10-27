#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oth_sold_list.py — OnTheHouse "sold" list for a suburb: the free, un-rate-limited comparable-sales source for states with no
official sales layer (WA, QLD, SA, TAS, NT, ACT) and a cross-check elsewhere.

Purpose  Download the suburb's recent sold properties (24 rows per page, about the last 12 months) as one JSON list.
Inputs   --state wa --suburb east-perth --postcode 6004 [--pages 20] [--delay 2] [--out oth.json]
         URL pattern: https://www.onthehouse.com.au/sold/<state>/<suburb>-<postcode>?page=N  (a Chrome User-Agent is required; plain curl
         defaults may be refused). The page embeds its data as window.REDUX_DATA (JSON); this script reads searchProperties.results.content.
Output   --out JSON list, newest sale first, one row per property:
           {address, price, date, beds, baths, cars, type, land_m2, floor_m2, year_built, lat, lon, id, href, avm_price, avm_from, avm_to}
         address is "101/112-122 Goderich St, East Perth WA 6004" style; price and date are the last SOLD event (ISO date);
         land_m2 for a unit is the strata lot area when the site shows one; floor_m2 is the internal floor size when shown (often missing);
         href is the property detail page (it needs the numeric id at its end; use it for strata lot area, levies in the listing copy and
         the sale history); avm_* is OnTheHouse's automated estimate (a model value, not a sale: never use it as a comparable).
Caveats  * 12-month window only: it cannot give long-run growth. * Price may be missing (undisclosed). * type is the site's label
           (House / Unit / Apartment / Townhouse / Commercial): filter before using. * One request per page with a polite delay (default 2 s);
           stop at the last page (results.totalPages). * Status 403/429 or a page without REDUX_DATA ends the run with what it has.
Needs only the Python standard library.

usage:
  python oth_sold_list.py --state wa --suburb east-perth --postcode 6004 --pages 20 --out oth.json
"""
import sys, re, json, time, argparse, urllib.request, urllib.error
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-AU,en;q=0.9"}
MARK = "window.REDUX_DATA = "

def fetch(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e: return e.code, ""
    except Exception as e: return 0, repr(e)[:80]

def results(html):
    """searchProperties.results dict from the embedded REDUX_DATA, or None."""
    i = html.find(MARK)
    if i < 0: return None
    try: data, _ = json.JSONDecoder().raw_decode(html[i + len(MARK):])
    except ValueError: return None
    return (data.get("searchProperties") or {}).get("results")

def row(p):
    ad = p.get("address") or {}; ls = p.get("lastSale") or {}; g = p.get("guesstimate") or {}
    num = ad.get("streetNumber") or ""; unit = ad.get("unitNumber")
    street = " ".join(x for x in (ad.get("streetName"), ad.get("streetType")) if x).title()
    addr = "%s%s %s, %s %s %s" % ((unit + "/") if unit else "", num, street, (ad.get("suburb") or "").title(), ad.get("stateCode") or "", ad.get("postCode") or "")
    href = next((l.get("href") for l in p.get("links", []) if l.get("rel") == "othWebUrl"), None)
    loc = ad.get("location") or {}
    return {"address": re.sub(r"\s+", " ", addr).strip(), "price": ls.get("salePrice"), "date": ls.get("eventDate"), "beds": p.get("beds"), "baths": p.get("baths"),
            "cars": p.get("carSpaces"), "type": p.get("type"), "land_m2": p.get("landSize"), "floor_m2": p.get("floorSize"), "year_built": p.get("yearBuilt"),
            "lat": loc.get("lat"), "lon": loc.get("lon"), "id": p.get("othPropertyId") or p.get("id"), "href": href,
            "avm_price": g.get("price"), "avm_from": g.get("fromPrice"), "avm_to": g.get("toPrice")}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", required=True, help="wa, nsw, vic, qld, sa, tas, nt, act"); ap.add_argument("--suburb", required=True, help="slug, e.g. east-perth")
    ap.add_argument("--postcode", required=True); ap.add_argument("--pages", type=int, default=20, help="maximum pages to fetch (24 rows each, default 20)")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between pages (default 2)"); ap.add_argument("--out", default="oth.json")
    a = ap.parse_args(); out = []; seen = set(); total = None; total_el = None
    for n in range(1, a.pages + 1):
        url = "https://www.onthehouse.com.au/sold/%s/%s-%s?page=%d" % (a.state.lower(), a.suburb.lower(), a.postcode, n)
        st, h = fetch(url)
        res = results(h) if st == 200 else None
        if res is None:
            print("page %d: HTTP %s, no data (blocked, wrong slug, or past the end) - stopping" % (n, st), file=sys.stderr); break
        total = res.get("totalPages"); total_el = res.get("totalElements"); added = 0
        for p in res.get("content", []):
            r = row(p); key = (r["id"], r["date"], r["price"])
            if key not in seen: seen.add(key); out.append(r); added += 1
        print("page %d/%s: %d rows (+%d new)" % (n, total, len(res.get("content", [])), added), flush=True)
        if not added or (total and n >= total): break
        time.sleep(a.delay)
    out.sort(key=lambda r: str(r["date"] or ""), reverse=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dates = [r["date"] for r in out if r["date"]]
    print("written %s | %d rows | %s to %s | site reports %s sold" % (a.out, len(out), min(dates) if dates else None, max(dates) if dates else None, total_el))

if __name__ == "__main__":
    main()
