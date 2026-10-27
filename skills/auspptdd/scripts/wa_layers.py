#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wa_layers.py — one-shot Western Australia point check against the free Landgate SLIP public services (+ Main Roads WA traffic).

Purpose: for a point (lon, lat) run every layer listed in the config - address, cadastre, plan extent, planning scheme zone / R-code / MRS,
heritage (State Register, Heritage List, Local Heritage Survey, Heritage Areas), flood (DWER 8 / 21 / 23 / 54 and flood level points),
bushfire prone, acid sulfate soil, contaminated sites, Bush Forever, noise (SPP 5.4), airports, drainage, sewer, schools, 2 m contours,
roads (18 + 19), rail stops and Main Roads traffic - and write one JSON.

Inputs   --lon --lat (WGS84)   [--near 1500] [--config templates/layers-WA.json] [--out layers.json]
         Every service / layer number / buffer / field lives in the config (keys per layer: label, service, layer, near, fields, note;
         optional: where, base, near_only, max_rows). Add or fix a layer by editing the config, not this script.
         near: metres for the extra buffer query; "default" = the --near option; 0 = point query only.
Output   --out JSON: {"point", "queried", "config", "layers": {key: {label, service, layer, note, point_hits, point_rows[],
         near_m, near_hits, nearest_m, near_rows[] (each with _dist_m, nearest first), error}}} and a one-line summary per layer.
Caveats  * An empty point result is "not detected" ONLY where the layer covers the area (read the layer's note): DWER flood layers cover
           studied rivers only; there is no free WA landslip layer, no development-application register and no ANEF contour layer.
         * nearest_m is measured to the closest vertex of the returned geometry, so it is approximate for long lines / large polygons.
         * Strata units have no cadastre address record in SLIP: the point returns the parent parcel (see plan_extent for the SP).
         * Layer numbers change between SLIP releases; the dataset ID in the label (e.g. DWER-020) is the stable name. Errors are
           recorded per layer in "error" and never stop the run.
Needs only the Python standard library.

usage:
  python wa_layers.py --lon 115.8694 --lat -31.9603 [--near 1500] [--config ../templates/layers-WA.json] --out layers.json
"""
import sys, os, json, math, time, argparse, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 auspptdd/0.4"}
DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "layers-WA.json")

def get(url, params, t=60):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=t).read().decode("utf-8", "replace"))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lon", type=float, required=True); ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--near", type=int, default=1500, help='buffer in metres for layers whose config near is "default" (default 1500)')
    ap.add_argument("--config", default=DEFAULT_CONFIG, help="layer config JSON (default: ../templates/layers-WA.json)")
    ap.add_argument("--out", default="layers.json"); ap.add_argument("--workers", type=int, default=6, help="parallel requests (default 6)")
    ap.add_argument("--keep-geom", action="store_true", help="also store the geometry of the first near row of each layer")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8")); lon, lat = a.lon, a.lat
    K = 111320 * math.cos(math.radians(lat))

    def dist_m(x, y): return math.hypot((x - lon) * K, (y - lat) * 110540)
    def geom_dist(g):
        pts = []
        for r in (g or {}).get("rings", []) + (g or {}).get("paths", []): pts += r
        if g and "x" in g: pts.append([g["x"], g["y"]])
        return round(min((dist_m(x, y) for x, y in pts), default=None)) if pts else None

    def q(spec, dist=None):
        base = spec.get("base", cfg["base"])
        p = {"geometry": "%f,%f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
             "outFields": spec.get("fields", "*"), "returnGeometry": "true" if dist else "false", "outSR": "4326", "f": "json"}
        if dist: p["distance"] = str(dist); p["units"] = "esriSRUnit_Meter"
        if spec.get("where"): p["where"] = spec["where"]
        for attempt in range(2):
            try:
                r = get("%s/%s/MapServer/%s/query" % (base, spec["service"], spec["layer"]), p)
                if "error" in r: raise Exception(str(r["error"])[:150])
                return r, None
            except Exception as e:
                err = repr(e)[:200]; time.sleep(2)
        return {}, err

    def run(item):
        key, spec = item; max_rows = spec.get("max_rows", 12); clean = lambda at: {k: v for k, v in at.items() if v not in (None, "", " ")}
        res = {"label": spec.get("label"), "service": spec["service"], "layer": spec["layer"], "note": spec.get("note"), "error": None}
        nm = a.near if spec.get("near") == "default" else (spec.get("near") or 0)
        if not spec.get("near_only"):
            r, err = q(spec); fs = r.get("features", [])
            res.update({"point_hits": len(fs), "point_rows": [clean(f["attributes"]) for f in fs[:max_rows]]}); res["error"] = err
        if nm:
            r, err = q(spec, nm); fs = r.get("features", [])
            rows = sorted(({**clean(f["attributes"]), "_dist_m": geom_dist(f.get("geometry"))} for f in fs), key=lambda d: (d["_dist_m"] is None, d["_dist_m"] or 0))
            res.update({"near_m": nm, "near_hits": len(fs), "nearest_m": rows[0]["_dist_m"] if rows else None, "near_rows": rows[:max_rows]})
            if a.keep_geom and fs: res["near_first_geom"] = fs[0].get("geometry")
            res["error"] = res["error"] or err
        return key, res

    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex: results = list(ex.map(run, cfg["layers"].items()))
    out = {"point": [lon, lat], "queried": time.strftime("%Y-%m-%d"), "config": cfg.get("name"), "config_tested": cfg.get("tested"), "layers": dict(results)}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    nerr = 0
    for k, r in out["layers"].items():
        bits = []
        if "point_hits" in r: bits.append("point=%d" % r["point_hits"])
        if "near_m" in r: bits.append("within %dm=%d, nearest=%s m" % (r["near_m"], r["near_hits"], r["nearest_m"]))
        if r["error"]: bits.append("ERROR " + r["error"][:80]); nerr += 1
        print("%-18s %s" % (k, "; ".join(bits)))
    print("written", a.out, "|", len(out["layers"]), "layers |", nerr, "with errors")

if __name__ == "__main__":
    main()
