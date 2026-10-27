#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nsw_lot_terrain.py — NSW lot boundary + nearby roads + 2 m contours + street side + ground profile, from one point.

Sources (all free, no login):
  lot boundary  SIX Valuation MapServer L9 (point query)                -> ring.json
  roads         NSW Transport Theme L5 RoadSegment (distance query);
                OSM Overpass only as fallback                            -> roads.json
  contours      NSW Elevation & Depth Theme L2 (polygon query, +45 m)    -> contours.json (local metres, origin = the point)
  cross-check   opentopodata SRTM30 corner elevations (printed only)
Then prints: side lengths, area, nearest road per side, profile from each side, and the street-side profile summary.
Strata guard: before any terrain work it queries NSW_Cadastre L9 at the point; if the lot is a strata plan (lotidstring contains "SP",
or hasstratum == 2) it prints "strata lot (...): terrain is not meaningful for a unit, skipping (use --force to override)" and exits 0
(the lot boundary of a unit block is the whole parcel, so slope/side/profile say nothing about one unit). --force runs anyway.

usage:
  python nsw_lot_terrain.py --lon 152.0939 --lat -32.7396 [--out-dir .] [--road-radius 120] [--contour-buffer 45] [--force]
  python nsw_lot_terrain.py --address "2 Example St, Suburb NSW 2000"     (geocodes first)
Next: python site_profile_svg.py --lon .. --lat .. --label ".." --sublabel ".." --out-dir .
"""
import sys, os, json, math, argparse, urllib.request, urllib.parse
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 auspptdd/0.2"}
SIXV = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer"
CAD = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer"
ELEV = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Elevation_and_Depth_Theme/MapServer"
TRANS = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Transport_Theme/MapServer"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"]

def get(url, params=None, post=False, t=90):
    data = urllib.parse.urlencode(params or {})
    req = urllib.request.Request(url if post or not data else url + "?" + data, data=data.encode() if post else None, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=t).read().decode("utf-8", "replace"))

def strata_lot(lon, lat):
    """Return the cadastre lotidstring if the point is in a strata lot (SP plan or hasstratum == 2), else None. Fails open (None) on any error."""
    try:
        r = get(CAD + "/9/query", {"f": "json", "geometry": "%f,%f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "lotidstring,hasstratum", "returnGeometry": "false"})
        for f in r.get("features", []):
            at = f["attributes"]; lid = str(at.get("lotidstring") or "")
            if "SP" in lid.upper() or at.get("hasstratum") == 2: return lid
    except Exception as e: print("cadastre strata check failed (continuing):", repr(e)[:100], file=sys.stderr)
    return None

def geocode(addr):
    c = get("https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates", {"f": "json", "singleLine": addr, "maxLocations": 1, "outSR": 4326})["candidates"][0]
    print("geocode:", c["address"], "score", c["score"], file=sys.stderr); return c["location"]["x"], c["location"]["y"]

def seg_inter(p, q, a, b):
    x1, y1 = p; x2, y2 = q; x3, y3 = a; x4, y4 = b
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-12: return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den; u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
    return t if 0 <= t <= 1 and 0 <= u <= 1 else None
def dseg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p; dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L)); return math.hypot(px - ax - t * dx, py - ay - t * dy)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lon", type=float); ap.add_argument("--lat", type=float); ap.add_argument("--address")
    ap.add_argument("--out-dir", default="."); ap.add_argument("--road-radius", type=int, default=120); ap.add_argument("--contour-buffer", type=int, default=45)
    ap.add_argument("--force", action="store_true", help="run even if the point is in a strata lot (SP plan)")
    a = ap.parse_args()
    if a.address and (a.lon is None or a.lat is None): a.lon, a.lat = geocode(a.address)
    if a.lon is None: ap.error("--lon/--lat or --address required")
    lon0, lat0 = a.lon, a.lat
    if not a.force:
        sl = strata_lot(lon0, lat0)
        if sl: print("strata lot (%s): terrain is not meaningful for a unit, skipping (use --force to override)" % sl); return
    os.makedirs(a.out_dir, exist_ok=True)
    K = 111320 * math.cos(math.radians(lat0)); xy = lambda p: ((p[0] - lon0) * K, (p[1] - lat0) * 111320)
    pt = {"f": "json", "geometry": "%f,%f" % (lon0, lat0), "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "true", "outSR": 4326}
    # 1 boundary
    b = get(SIXV + "/9/query", pt)
    if not b.get("features"): sys.exit("no lot boundary at this point (SIX Valuation L9)")
    ring = b["features"][0]["geometry"]["rings"][0]; propid = b["features"][0]["attributes"].get("propid")
    json.dump(ring, open(os.path.join(a.out_dir, "ring.json"), "w", encoding="utf-8"))
    R = [xy(p) for p in ring]; n = len(R) - 1
    A = 0.5 * abs(sum(R[i][0] * R[i + 1][1] - R[i + 1][0] * R[i][1] for i in range(n)))
    print("propid", propid, "| vertices", n, "| area %.1f m2" % A, "| sides", ["%.1f" % math.dist(R[i], R[i + 1]) for i in range(n)])
    # 2 roads: Transport theme first
    roads = []
    try:
        q = dict(pt); q.update({"distance": a.road_radius, "units": "esriSRUnit_Meter"})
        rr = get(TRANS + "/5/query", q)
        if "error" in rr: raise Exception(rr["error"])
        for f in rr.get("features", []):
            at = f["attributes"]; nm = {k: at.get(k) for k in ("roadnamebase", "roadnametype", "roadnamesuffix")}
            for path in f["geometry"]["paths"]: roads.append((nm, at.get("functionhierarchy"), path))
        print("roads: NSW Transport Theme L5,", len(roads), "segments", file=sys.stderr)
    except Exception as ex:
        print("transport theme failed:", repr(ex)[:120], "-> trying Overpass", file=sys.stderr)
        qq = "[out:json][timeout:25];way[highway](around:%d,%f,%f);out tags geom;" % (a.road_radius, lat0, lon0)
        for u in OVERPASS:
            try:
                o = get(u, {"data": qq}, post=True, t=60)
                for e in o["elements"]:
                    roads.append((e["tags"].get("name", "?"), e["tags"].get("highway"), [(g["lon"], g["lat"]) for g in e["geometry"]]))
                print("roads: Overpass", u, file=sys.stderr); break
            except Exception as ex2: print("overpass fail", u, repr(ex2)[:80], file=sys.stderr)
    json.dump(roads, open(os.path.join(a.out_dir, "roads.json"), "w", encoding="utf-8"))
    sidebest = {}
    for nm, hw, pts in roads:
        P = [xy(p) for p in pts]
        if len(P) < 2: continue
        for i in range(n):
            mid = ((R[i][0] + R[i + 1][0]) / 2, (R[i][1] + R[i + 1][1]) / 2)
            d = min(dseg(mid, p, q2) for p, q2 in zip(P, P[1:]))
            if i not in sidebest or d < sidebest[i][0]: sidebest[i] = (d, nm if isinstance(nm, str) else "%s %s" % (nm.get("roadnamebase"), nm.get("roadnametype")), hw)
    for i in range(n):
        if i in sidebest: print("side %d: nearest road %s (hierarchy %s) at %.1f m" % (i, sidebest[i][1], sidebest[i][2], sidebest[i][0]))
    front = min(sidebest, key=lambda i: sidebest[i][0]) if sidebest else 0
    # 3 contours
    pq = {"f": "json", "geometry": json.dumps({"rings": [ring], "spatialReference": {"wkid": 4326}}), "geometryType": "esriGeometryPolygon", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "true", "outSR": 4326, "distance": a.contour_buffer, "units": "esriSRUnit_Meter"}
    r = get(ELEV + "/2/query", pq)
    if "error" in r: sys.exit("contour error: %s" % r["error"])
    cont = []
    for f in r["features"]:
        e = f["attributes"].get("elevation", f["attributes"].get("ELEVATION"))
        for path in f["geometry"]["paths"]: cont.append((e, [xy(p) for p in path]))
    json.dump(cont, open(os.path.join(a.out_dir, "contours.json"), "w", encoding="utf-8"))
    print("contours:", sorted({e for e, _ in cont}))
    # 4 profiles
    cx = sum(p[0] for p in R[:-1]) / n; cy = sum(p[1] for p in R[:-1]) / n
    def profile(i):
        mid = ((R[i][0] + R[i + 1][0]) / 2, (R[i][1] + R[i + 1][1]) / 2); far = (2 * cx - mid[0], 2 * cy - mid[1]); L = math.dist(mid, far)
        ux, uy = (far[0] - mid[0]) / L, (far[1] - mid[1]) / L
        P0 = (mid[0] - ux * 14, mid[1] - uy * 14); P1 = (far[0] + ux * 14, far[1] + uy * 14); TL = math.dist(P0, P1); hits = []
        for e, path in cont:
            for s1, s2 in zip(path, path[1:]):
                t = seg_inter(P0, P1, s1, s2)
                if t is not None: hits.append((round(t * TL - 14, 1), e))
        hits.sort(); return L, hits
    for i in range(n):
        L, hits = profile(i); print("profile from side %d (depth %.1f m):" % (i, L), hits)
    L, hits = profile(front)
    def el(x):
        if not hits: return None
        if x <= hits[0][0]: return hits[0][1]
        for (x1, e1), (x2, e2) in zip(hits, hits[1:]):
            if x1 <= x <= x2: return e1 + (e2 - e1) * (x - x1) / (x2 - x1) if x2 > x1 else e1
        return hits[-1][1]
    summary = {"propid": propid, "area_m2": round(A, 1), "front_side": front, "front_road": sidebest.get(front, (None, None, None))[1], "depth_m": round(L, 1),
               "street_el": el(-7.5), "front_el": el(0), "rear_el": el(L), "fall_m": round((el(0) or 0) - (el(L) or 0), 2) if hits else None,
               "gradient_pct": round(((el(0) or 0) - (el(L) or 0)) / L * 100, 1) if hits and L else None, "profile": hits}
    json.dump(summary, open(os.path.join(a.out_dir, "terrain_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("SUMMARY", json.dumps(summary, ensure_ascii=False))
    try:
        rr = get("https://api.opentopodata.org/v1/srtm30m", {"locations": "|".join("%f,%f" % (p[1], p[0]) for p in ring[:-1])}, t=60)
        print("SRTM30 corner elevations (cross-check):", [x["elevation"] for x in rr["results"]])
    except Exception as e: print("srtm cross-check failed:", repr(e)[:80], file=sys.stderr)

if __name__ == "__main__":
    main()
