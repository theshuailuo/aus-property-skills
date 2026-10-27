#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
abs_g37.py — social-housing share from ABS Census 2021 table G37, at suburb (SAL) and community (SA2) scope.

1. Point -> SAL and SA2 codes via ABS ASGS2021 ArcGIS services.
2. ABS Data API C21_G37_SAL / C21_G37_SA2 (CSV with labels), tenure = state housing authority + community housing provider,
   dwelling structure = Total, divided by total dwellings.
Report BOTH scopes (they can differ by an order of magnitude). SA1 (street block) is not in the API — needs the Census DataPack.

usage: python abs_g37.py --lon 152.0939 --lat -32.7396 [--out social_housing.json]
"""
import sys, csv, io, json, argparse, urllib.request, urllib.parse
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 auspptdd/0.2"}
def get(url, params=None, raw=False):
    u = url + ("?" + urllib.parse.urlencode(params) if params else "")
    b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90).read()
    return b.decode("utf-8", "replace") if raw else json.loads(b.decode("utf-8", "replace"))
def code(level, lon, lat):
    r = get("https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/%s/MapServer/0/query" % level, {"f": "json", "geometry": "%f,%f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "false"})
    a = r["features"][0]["attributes"]; low = {k.lower(): v for k, v in a.items()}
    return low.get("%s_code_2021" % level.lower()), low.get("%s_name_2021" % level.lower())
def g37(flow, region):
    txt = get("https://data.api.abs.gov.au/rest/data/ABS,%s/..%s..?format=csvfilewithlabels" % (flow, region), raw=True)
    tot = soc = 0
    for r in csv.DictReader(io.StringIO(txt)):
        if r.get("Dwelling structure") != "Total" and r.get("STRD") != "_T": continue
        v = float(r.get("OBS_VALUE") or 0); ten = r.get("Tenure and landlord type", "")
        if ten == "Total": tot = v
        elif "housing authority" in ten or "Community housing" in ten: soc += v
    return {"total_dwellings": tot, "social_housing": soc, "pct": round(soc / tot * 100, 2) if tot else None}
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lon", type=float, required=True); ap.add_argument("--lat", type=float, required=True); ap.add_argument("--out", default="social_housing.json")
    a = ap.parse_args(); out = {}
    for level, flow in (("SAL", "C21_G37_SAL"), ("SA2", "C21_G37_SA2")):
        try:
            c, n = code(level, a.lon, a.lat); out[level] = {"code": c, "name": n}; out[level].update(g37(flow, c))
        except Exception as e: out[level] = {"error": repr(e)[:200]}
        print(level, json.dumps(out[level], ensure_ascii=False))
    out["SA1"] = "not in ABS Data API; needs Census DataPack download (list as a next step)"
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print("written", a.out)
if __name__ == "__main__":
    main()
