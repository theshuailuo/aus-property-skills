#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nsw_layers.py — one-shot NSW point check: lot, land value, planning, hazards, SEPP Housing, DA, roads.

Queries (all free, no login) and writes layers.json:
  cadastre   NSW_Cadastre L9 (Lot/DP)                                   SIX Valuation L9 boundary (propid) + L5 attributes by propid
  planning   ePlanning EPI_Primary_Planning_Layers L0-L6
  hazards    Planning/Hazard L1 Flood (10 LGAs only!), L2 Landslide;  Protection L1 ASS, L2 ANEF, L7 Riparian, L9 Scenic, L10 Biodiversity, L12 Env-sensitive
  bushfire   Fire/BFPL L0 (+ nearest patch within --near m)
  policy     SEPP_Housing_2021 L2 STRA, L3 TOD, L4 Accelerated TOD, L5 Deferred TOD, L6 Town Centres (+ nearest within 1200 m)
  valuation  SIX Valuation L5 by propid AND by the parent street address -> ALL distinct propids as `valuation` [{propid, prop_area, lv, ...}]
             (a building can hold two strata schemes = two propids). If the cadastre lot is an SP (strata plan) the same list is also
             written as `strata_schemes` with a note: prop_area is the parcel/scheme land area, NOT the building footprint or a unit's area.
  DA         DA_Tracking L0 by street+suburb (UPPER/LIKE) and within 300 m; COST_OF_DEVELOPMENT (a string in the layer) is converted to a
             float and `da_large` lists DAs >= --da-large-min (default $5M): address, status, cost, lodged year
  roads      Transport Theme L5 within --near m (hierarchy<=4 = main roads), L7 railway within 800 m
             (railontype is decoded from the layer's own field domain; `underground_likely` = in tunnel -> surface rail noise may not apply,
             but check whether it is a tunnel such as Sydney Metro before relying on it)
  council    optional --council-config JSON: {"name":..,"service":..,"layers":{"label":{"id":159,"field":"Risk","near":500}, ...},
               "state_fallback": {"service":..,"layers":{...}},   # queried like council layers; output tagged source:"state"
               "pdf_maps": {"name": "https://...pdf"}}            # emitted as {"status":"not_covered","pdf":url} rows
             (see ../templates/council-northern-beaches.json and council-north-sydney.json). When a council has no GIS layer for a hazard,
             an empty result is NOT proof of "not affected": the pdf_maps rows point to the PDF the reader must check.

usage:
  python nsw_layers.py --lon 152.0939 --lat -32.7396 --street "SALAMANDER WAY" --suburb "SALAMANDER BAY" [--council-config ../templates/council-port-stephens.json] [--out layers.json]
  python nsw_layers.py --address "2 Example St, Suburb NSW 2000" ...
An empty result is printed as [] — it means "not detected" ONLY where the layer covers that LGA (see state-NSW.md).
Extra option: --da-large-min 5000000 (dollar threshold for the da_large list).
"""
import sys, os, re, json, math, argparse, urllib.request, urllib.parse, time
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 auspptdd/0.2"}
B = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
SIXV = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer"
CAD = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer"
EPI, HAZ, PRO, BFPL, SEPPH, DA = (B + s for s in ("Planning/EPI_Primary_Planning_Layers/MapServer", "Planning/Hazard/MapServer", "Planning/Protection/MapServer", "Fire/BFPL/MapServer", "Planning/SEPP_Housing_2021/MapServer", "Planning/DA_Tracking/MapServer"))
TRANS = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Transport_Theme/MapServer"
SKIP = {"Shape__Area", "Shape__Length", "Shape_Area", "Shape_Length", "shape_Area", "shape_Length", "OBJECTID", "GlobalID"}

def get(url, params, t=90):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=t).read().decode("utf-8", "replace"))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lon", type=float); ap.add_argument("--lat", type=float); ap.add_argument("--address")
    ap.add_argument("--street", help="street name + type in caps for DA search, e.g. 'SALAMANDER WAY'"); ap.add_argument("--suburb", help="suburb in caps")
    ap.add_argument("--council-config"); ap.add_argument("--near", type=int, default=1500); ap.add_argument("--out", default="layers.json")
    ap.add_argument("--da-large-min", type=float, default=5e6, help="dollar threshold for the da_large list (default 5,000,000)")
    a = ap.parse_args()
    if a.address and (a.lon is None or a.lat is None):
        c = get("https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates", {"f": "json", "singleLine": a.address, "maxLocations": 1, "outSR": 4326})["candidates"][0]
        a.lon, a.lat = c["location"]["x"], c["location"]["y"]; print("geocode:", c["address"], c["score"], file=sys.stderr)
    if a.lon is None: ap.error("--lon/--lat or --address required")
    lon, lat = a.lon, a.lat; K = 111320 * math.cos(math.radians(lat))
    def mind(geom):
        best = 1e9
        for ring in geom.get("rings") or geom.get("paths") or []:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                ax, ay = (x1 - lon) * K, (y1 - lat) * 111320; bx, by = (x2 - lon) * K, (y2 - lat) * 111320
                dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy; t = 0 if L == 0 else max(0, min(1, (-(ax * dx + ay * dy)) / L))
                best = min(best, math.hypot(ax + t * dx, ay + t * dy))
        return round(best)
    def pq(base, lid, extra=None, geom=False):
        p = {"f": "json", "geometry": "%f,%f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "true" if geom else "false", "outSR": 4326}
        if extra: p.update(extra)
        try:
            r = get(base + "/%s/query" % lid, p)
            if "error" in r: return {"ERR": r["error"]}
            out = []
            for f in r.get("features", []):
                d = {k: v for k, v in f["attributes"].items() if v not in (None, "", " ") and k not in SKIP}
                if geom and f.get("geometry"): d["_dist_m"] = mind(f["geometry"])
                out.append(d)
            return sorted(out, key=lambda d: d.get("_dist_m", 0))
        except Exception as e: return {"EXC": repr(e)[:200]}
    near = lambda m: {"distance": m, "units": "esriSRUnit_Meter"}
    def top(x, n):  # slice only when the query returned a list (errors come back as dicts)
        return x[:n] if isinstance(x, list) else x
    out = {"point": [lon, lat], "queried": time.strftime("%Y-%m-%d")}
    # lot
    out["cadastre_lot"] = pq(CAD, 9)
    bnd = pq(SIXV, 9); out["valuation_boundary"] = bnd
    propid = bnd[0].get("propid") if isinstance(bnd, list) and bnd else None
    def l5(where):
        r = get(SIXV + "/5/query", {"f": "json", "where": where, "outFields": "*", "returnGeometry": "false"})
        return [{k: v for k, v in f["attributes"].items() if v not in (None, "", " ")} for f in r.get("features", [])] if "error" not in r else []
    def mnum(x):
        d = re.sub(r"[^0-9.]", "", str(x or "")); return float(d) if d else None
    rows5 = []
    if propid:
        try: rows5 = l5("propid=%s" % propid); out["valuation_L5"] = rows5
        except Exception as e: out["valuation_L5"] = {"EXC": repr(e)[:200]}
    # parent street address (taken from the propid row) -> every L5 row at that address: one building can carry several propids
    try:
        parent = next((str(r.get("address", "")).strip() for r in rows5 if r.get("address")), "").split(" NSW")[0].strip()  # "150 PACIFIC HWY, NORTH SYDNEY"
        if parent: rows5 = rows5 + l5("address LIKE '%s%%'" % parent.replace("'", "''"))
    except Exception as e: out["valuation_address_EXC"] = repr(e)[:200]
    seen, val = set(), []
    for r in rows5:
        pid = r.get("propid")
        if pid in seen: continue
        seen.add(pid)
        hist = [{"date": r.get("val%d_bd" % i), "lv": mnum(r.get("val%d_lv" % i))} for i in range(1, 6) if r.get("val%d_lv" % i)]
        val.append({"propid": pid, "address": str(r.get("address", "")).strip(), "prop_area": r.get("prop_area"), "prop_area_m2": mnum(str(r.get("prop_area", "")).split(" ")[0]),
                    "lv": hist[0]["lv"] if hist else None, "lv_date": hist[0]["date"] if hist else None, "lv_history": hist, "zone_desc": r.get("zone_desc"),
                    "basis_desc": r.get("basis_desc"), "is_cadastre_point_propid": pid == propid})
    out["valuation"] = val
    cl = out["cadastre_lot"][0] if isinstance(out["cadastre_lot"], list) and out["cadastre_lot"] else {}
    lotid = str(cl.get("lotidstring") or "")
    out["is_strata_lot"] = ("SP" in lotid.upper()) or cl.get("hasstratum") == 2
    if out["is_strata_lot"]:
        out["strata_schemes"] = val
        out["strata_note"] = ("Cadastre lot %s is a strata plan. valuation[].prop_area is the land area of the whole parcel/scheme (a building can be split across two schemes/propids), "
                              "NOT the building footprint and NOT a unit's area; valuation[].lv is the scheme-level land value apportioned between building parcels, not a unit's." % lotid)
    # planning
    for lid, nm in [(0, "heritage"), (1, "fsr"), (2, "zone"), (3, "land_reservation"), (4, "lot_size"), (5, "height"), (6, "land_application")]: out["epi_" + nm] = pq(EPI, lid)
    out["haz_flood_state_10LGA_only"] = pq(HAZ, 1); out["haz_landslide"] = pq(HAZ, 2); out["haz_landslide_near100"] = pq(HAZ, 2, near(100), geom=True)
    for lid, nm in [(1, "acid_sulfate"), (2, "anef"), (7, "riparian"), (9, "scenic"), (10, "biodiversity"), (12, "env_sensitive")]: out["pro_" + nm] = pq(PRO, lid)
    out["bfpl"] = pq(BFPL, 0); out["bfpl_near"] = top(pq(BFPL, 0, near(a.near), geom=True), 4)
    for lid, nm in [(2, "stra"), (3, "tod"), (4, "tod_accelerated"), (5, "tod_deferred"), (6, "town_centres")]:
        out["sepph_" + nm] = pq(SEPPH, lid); out["sepph_%s_near1200" % nm] = top(pq(SEPPH, lid, near(1200), geom=True), 3)
    # DA
    if a.street and a.suburb:
        try:
            r = get(DA + "/0/query", {"f": "json", "where": "UPPER(SITE_ADDRESS) LIKE '%%%s%%' AND UPPER(SUBURBNAME)='%s'" % (a.street.upper(), a.suburb.upper()), "outFields": "*", "returnGeometry": "false"})
            out["da_street"] = [{k: v for k, v in f["attributes"].items() if v not in (None, "", " ") and k not in SKIP} for f in r.get("features", [])] if "error" not in r else {"ERR": r["error"]}
        except Exception as e: out["da_street"] = {"EXC": repr(e)[:200]}
    das = pq(DA, 0, near(300)); out["da_within300"] = das
    if isinstance(das, list):
        for d in das:  # the layer stores the cost as a string
            c = d.get("COST_OF_DEVELOPMENT")
            try: d["COST_OF_DEVELOPMENT"] = float(str(c).replace(",", "").replace("$", "")) if c not in (None, "") else None
            except ValueError: pass
        out["da_large"] = sorted([{"address": d.get("SITE_ADDRESS") or d.get("PRIMARY_ADDRESS"), "status": d.get("STATUS"), "cost": d["COST_OF_DEVELOPMENT"],
                                   "lodged_year": int(str(d.get("LODGEMENT_DATE") or d.get("SUBMITTED_DATE") or "0")[:4]) or None, "app_no": d.get("PLANNING_PORTAL_APP_NUMBER"),
                                   "type": d.get("TYPE_OF_DEVELOPMENT"), "desc": str(d.get("DEVELOPMENT_DETAILED_DESC") or "").strip()[:160], "dist_m": d.get("_dist_m")}
                                  for d in das if isinstance(d.get("COST_OF_DEVELOPMENT"), float) and d["COST_OF_DEVELOPMENT"] >= a.da_large_min], key=lambda r: -r["cost"])
    # roads / rail
    rs = pq(TRANS, 5, near(a.near), geom=True)
    if isinstance(rs, list):
        out["roads_main_within_near"] = [{"name": "%s %s" % (r.get("roadnamebase"), r.get("roadnametype")), "hierarchy": r.get("functionhierarchy"), "dist_m": r.get("_dist_m")} for r in rs if (r.get("functionhierarchy") or 9) <= 4][:8]
        out["roads_local_within120"] = sorted({("%s %s" % (r.get("roadnamebase"), r.get("roadnametype")), r.get("functionhierarchy")) for r in rs if r.get("_dist_m", 1e9) <= 120}, key=lambda x: x[0])
    else: out["roads_main_within_near"] = rs
    # railway: decode railontype from the layer's own field domain (OnGround / OnBridge / InTunnel / OnCulvert)
    rails = pq(TRANS, 7, near(800), geom=True)
    if isinstance(rails, list):
        dom_rail, dom_stat, sub, domain_ok = {}, {}, {}, False
        try:
            lj = get(TRANS + "/7", {"f": "json"})
            for fld in lj.get("fields", []):
                cv = ((fld.get("domain") or {}).get("codedValues")) or []
                if fld.get("name") == "railontype" and cv: dom_rail = {c["code"]: c["name"] for c in cv}; domain_ok = True
                if fld.get("name") == "operationalstatus" and cv: dom_stat = {c["code"]: c["name"] for c in cv}
            sub = {t["id"]: t["name"] for t in lj.get("types", [])}
        except Exception as e: print("railway domain lookup failed:", repr(e)[:100], file=sys.stderr)
        for r in rails:
            code = r.get("railontype"); nm = dom_rail.get(code)
            r["railontype_name"] = nm if nm else (None if code is None else str(code))
            r["class_name"] = sub.get(r.get("classsubtype")); r["operationalstatus_name"] = dom_stat.get(r.get("operationalstatus"))
            r["underground_likely"] = bool(nm and re.search(r"tunnel|underground", nm, re.I))
        live = [r for r in rails if r.get("operationalstatus") in (None, 1)] or rails
        n0 = live[0] if live else None
        out["railway_within800"] = top(rails, 8)
        out["railway_summary"] = {"n_segments": len(rails), "nearest_m": n0.get("_dist_m") if n0 else None, "nearest_class": n0.get("class_name") if n0 else None,
                                  "nearest_railontype": n0.get("railontype") if n0 else None, "nearest_railontype_name": n0.get("railontype_name") if n0 else None,
                                  "underground_likely": bool(n0 and n0["underground_likely"]), "all_underground_likely": bool(live) and all(r["underground_likely"] for r in live),
                                  "note": ("railontype decoded from the layer domain (InTunnel = underground). A tunnel can still be felt as vibration/ground-borne noise; check the operator's alignment."
                                           if domain_ok else "No railontype domain published: raw value kept. Check whether this is a tunnel (e.g. Sydney Metro) before treating it as surface rail.")}
    else: out["railway_within800"] = rails
    # council
    if a.council_config:
        cfg = json.load(open(a.council_config, encoding="utf-8")); cc = {}
        def run_layers(svc, layers, state=False):
            res = {}
            for label, spec in layers.items():
                r1 = pq(svc, spec["id"])
                if spec.get("near"): r2 = top(pq(svc, spec["id"], near(spec["near"]), geom=True), 4)
                else: r2 = None
                if state:
                    res[label] = {"source": "state", "service": svc, "rows": r1}
                    if r2 is not None: res[label + "_near%d" % spec["near"]] = {"source": "state", "service": svc, "rows": r2}
                else:
                    res[label] = r1
                    if r2 is not None: res[label + "_near%d" % spec["near"]] = r2
            return res
        cc.update(run_layers(cfg["service"], cfg.get("layers", {})))
        sf = cfg.get("state_fallback") or {}
        if sf.get("layers"): cc["state_fallback"] = run_layers(sf["service"], sf["layers"], state=True)
        # sibling entries of state_fallback that are marked unusable (e.g. a statewide flood layer with no coverage of this LGA)
        for k, v in sf.items():
            if isinstance(v, dict) and k != "layers" and v.get("usable") is False:
                cc.setdefault("state_fallback_unusable", {})[k] = {"status": "not_usable", "reason": v.get("reason")}
        if cfg.get("pdf_maps"): cc["pdf_maps"] = [{"name": k, "status": "not_covered", "pdf": u} for k, u in cfg["pdf_maps"].items()]
        out["council_" + cfg.get("name", "x")] = cc
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for k, v in out.items():
        if isinstance(v, list): print("%-36s %s" % (k, "[] (empty)" if not v else json.dumps(v[0], ensure_ascii=False, default=str)[:160] + (" ... +%d" % (len(v) - 1) if len(v) > 1 else "")))
        elif isinstance(v, dict) and ("ERR" in v or "EXC" in v): print("%-36s ERROR %s" % (k, str(v)[:140]))
        elif isinstance(v, dict):
            for kk, vv in v.items(): print("%-36s %s" % (k + "." + kk, "[] (empty)" if vv == [] else str(vv)[:150]))
            if k.startswith("council_") and v.get("pdf_maps"): print("NOTE: %d council map(s) are PDF-only (status not_covered): an empty council result above is not proof of 'not affected'." % len(v["pdf_maps"]))
    if out.get("strata_note"): print("STRATA:", out["strata_note"])
    if out.get("da_large"): print("da_large (>= $%.0f):" % a.da_large_min, json.dumps([(d["address"], d["status"], d["cost"], d["lodged_year"]) for d in out["da_large"][:6]], ensure_ascii=False))
    print("written", a.out)

if __name__ == "__main__":
    main()
