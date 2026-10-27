#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
nsw_comps_enrich.py — enrich a list of comparable sales with free official attributes.

Input: a CSV (address,price,date[,kind]) or JSON list [{"address":..,"price":..,"date":..}] — addresses as the Valuer General
writes them: "112A SALAMANDER WAY" (caps, street type abbreviated); the first row may be the subject (kind=subject).
For each row: SIX Valuation L5 (land area, land value, zone), distance to the subject point, landslip zone (council layer from
--council-config or state Hazard L2), BFPL category, SRTM30 elevation.  Output: comps.json ready for data.json "comps.items"
(price/LV, LV per m² computed; beds/floor/built left for aussie_slow_fetch.py; scores left for you to fill).

Units: an address that matches ^\d+[A-Z]?/ (e.g. "1503/150 PACIFIC HWY") is a strata unit. Its row is KEPT but the L5 land lookup is skipped
(land_m2 / lv / lv_m2 / p_lv stay empty: VG L5 carries the parent parcel, not the unit). If the parent street number + street equal the
subject's (subject = --subject-address, else the first row with kind=subject) the row is flagged same_building=true and dist_m=0; for a
unit in another building dist_m comes from the parent address point in L5 (geometry only). --building-json takes the output of
domain_building_profile.js (a list of {unit, date, price, beds, baths, cars}) and fills beds/baths/cars (and price/date when the row has
none) for same-building rows. level_hint is the level guessed from the unit number (1503 -> 15): verify, numbering schemes differ.

usage:
  python nsw_comps_enrich.py --suburb "SALAMANDER BAY" --lon 152.0939 --lat -32.7396 --in comps.csv [--council-config council-port-stephens.json --landslip-layer landslip] [--out comps.json]
  python nsw_comps_enrich.py --suburb "NORTH SYDNEY" --lon 151.2053 --lat -33.8364 --in comps.json --subject-address "1803/150 PACIFIC HWY" --building-json building.json
"""
import sys, os, json, csv, re, math, time, argparse, urllib.request, urllib.parse
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 auspptdd/0.2"}
SIXV = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer"
HAZ = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Hazard/MapServer"
BFPL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer"
def get(url, params, t=90):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=t).read().decode("utf-8", "replace"))
def num(s): return float(re.sub(r"[^0-9.]", "", str(s)) or 0)
UNIT_RE = re.compile(r"^(\d+[A-Z]?)/")
def parent_key(addr):
    """('150', 'PACIFIC') from '1503/150 PACIFIC HWY[, SUBURB ...]' or '150 Pacific Highway': street number + first street-name word."""
    t = re.sub(r"[^A-Z0-9 /-]", " ", addr.upper().split(",")[0]); t = UNIT_RE.sub("", t.strip()); w = t.split()
    return (w[0], w[1]) if len(w) > 1 else (w[0] if w else "", "")
def parent_address_point(addr, suburb):
    """Geometry only: L5 row at the parent street address -> (lon, lat) or None."""
    try:
        t = UNIT_RE.sub("", addr.upper().split(",")[0].strip()).replace("'", "''")
        rr = get(SIXV + "/5/query", {"f": "json", "where": "address LIKE '%s, %s%%'" % (t, suburb.upper()), "outFields": "propid", "returnGeometry": "true", "outSR": 4326})
        g = (rr.get("features") or [{}])[0].get("geometry"); return (g["x"], g["y"]) if g else None
    except Exception: return None
def pq(base, lid, x, y, fld):
    r = get(base + "/%d/query" % lid, {"f": "json", "geometry": "%f,%f" % (x, y), "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "false"})
    return ",".join(str(f["attributes"].get(fld)) for f in r.get("features", [])) or "-"

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suburb", required=True); ap.add_argument("--lon", type=float, required=True); ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out", default="comps.json")
    ap.add_argument("--council-config"); ap.add_argument("--landslip-layer", help="label of the landslip layer in the council config")
    ap.add_argument("--subject-address", help='subject address as the Valuer General writes it, e.g. "1803/150 PACIFIC HWY" (default: first row with kind=subject)')
    ap.add_argument("--building-json", help="output of domain_building_profile.js: list of {unit, date, price, beds, baths, cars}; fills same-building unit rows")
    a = ap.parse_args()
    rows = []
    if a.inp.lower().endswith(".json"): rows = json.load(open(a.inp, encoding="utf-8"))
    else:
        for r in csv.DictReader(open(a.inp, encoding="utf-8-sig")): rows.append(r)
    ls_base = ls_id = ls_fld = None
    if a.council_config and a.landslip_layer:
        cfg = json.load(open(a.council_config, encoding="utf-8")); spec = cfg["layers"][a.landslip_layer]; ls_base, ls_id, ls_fld = cfg["service"], spec["id"], spec["field"]
    K = 111320 * math.cos(math.radians(a.lat)); out = []
    bld = {}
    if a.building_json:
        for b in json.load(open(a.building_json, encoding="utf-8")): bld.setdefault(str(b.get("unit", "")).upper(), []).append(b)
    subj = a.subject_address or next((r["address"] for r in rows if str(r.get("kind", "")).lower() == "subject"), None)
    subj_key = parent_key(subj) if subj else None
    pcache = {}
    for r in rows:
        addr = r["address"].upper().strip(); price = num(r.get("price")); date = r.get("date", "")
        row = {"address": addr, "price": price, "date": date, "kind": r.get("kind", "sale")}
        mu = UNIT_RE.match(addr)
        if mu:  # strata unit: keep the row, skip the L5 land lookup (L5 would return the parent parcel, not the unit)
            unit = mu.group(1); same = bool(subj_key) and parent_key(addr) == subj_key
            row.update({"is_unit": True, "unit": unit, "same_building": same, "propid": None, "land_m2": None, "lv": None, "lv_date": None, "lv_m2": None, "p_lv": None, "zone": None,
                        "dist_m": 0 if same else None, "level_hint": int(unit[:-2]) if unit.isdigit() and len(unit) >= 3 else None,
                        "beds": None, "baths": None, "cars": None, "floor_m2": None, "built": None, "storeys": None, "wall": None, "reno": None, "street_side": None,
                        "scores": {"land": None, "slope": None, "condition": None}, "bookend": None, "note": "unit: no land/LV (VG L5 is the parent parcel)"})
            if same and unit in bld:  # fill from the building profile; prefer the sale whose date matches the row, else the latest
                cands = sorted(bld[unit], key=lambda b: str(b.get("date", "")), reverse=True)
                hit = next((b for b in cands if date and str(b.get("date", ""))[:7] == str(date)[:7]), cands[0])
                row.update({"beds": hit.get("beds"), "baths": hit.get("baths"), "cars": hit.get("cars")})
                if not price and hit.get("price"): row["price"] = num(hit["price"])
                if not date and hit.get("date"): row["date"] = hit["date"]
                row["note"] += "; beds/baths/cars from building profile (%s)" % hit.get("date")
            elif not same:
                pk = parent_key(addr)
                if pk not in pcache: pcache[pk] = parent_address_point(addr, a.suburb); time.sleep(1)
                if pcache[pk]: row.update({"lon": pcache[pk][0], "lat": pcache[pk][1], "dist_m": round(math.hypot((pcache[pk][1] - a.lat) * 111320, (pcache[pk][0] - a.lon) * K)), "dist_basis": "parent address point"})
            out.append(row); print(json.dumps(row, ensure_ascii=False)[:200], flush=True); continue
        try:
            # outFields=* : naming a field L5 does not have (e.g. 'strata', which lives on the sales layer L1) returns 400 "Failed to execute query"
            rr = get(SIXV + "/5/query", {"f": "json", "where": "address LIKE '%s, %s%%'" % (addr.replace("'", "''"), a.suburb.upper()), "outFields": "*", "returnGeometry": "true", "outSR": 4326})
            fs = rr.get("features", [])
            if "error" in rr: row["err"] = str(rr["error"])[:120]
        except Exception as e: fs = []; row["err"] = repr(e)[:100]
        if not fs:
            row["err"] = row.get("err") or "VG not found"; out.append(row); print(addr, "VG not found", file=sys.stderr); continue
        at = fs[0]["attributes"]; g = fs[0]["geometry"]; ar = num(str(at.get("prop_area", "")).split(" ")[0]); lv = num(at.get("val1_lv"))
        row.update({"propid": at.get("propid"), "land_m2": ar, "lv": lv, "lv_date": at.get("val1_bd"), "lv_m2": round(lv / ar) if ar else None, "p_lv": round(price / lv, 2) if lv and price else None,
                    "zone": at.get("zone_desc"), "lon": g["x"], "lat": g["y"], "dist_m": round(math.hypot((g["y"] - a.lat) * 111320, (g["x"] - a.lon) * K))})
        try: row["landslip"] = pq(ls_base, ls_id, g["x"], g["y"], ls_fld) if ls_base else pq(HAZ, 2, g["x"], g["y"], "LAY_CLASS")
        except Exception: row["landslip"] = "?"
        try: row["bfpl"] = pq(BFPL, 0, g["x"], g["y"], "Category")
        except Exception: row["bfpl"] = "?"
        try: row["elev"] = get("https://api.opentopodata.org/v1/srtm30m", {"locations": "%f,%f" % (g["y"], g["x"])}, t=40)["results"][0]["elevation"]
        except Exception: row["elev"] = None
        row.update({"beds": None, "baths": None, "floor_m2": None, "built": None, "storeys": None, "wall": None, "reno": None, "street_side": None, "scores": {"land": None, "slope": None, "condition": None}, "bookend": None, "note": ""})
        out.append(row); print(json.dumps(row, ensure_ascii=False)[:200], flush=True); time.sleep(1)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("written", a.out, len(out), "rows")

if __name__ == "__main__":
    main()
