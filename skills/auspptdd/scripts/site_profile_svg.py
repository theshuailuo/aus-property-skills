#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
site_profile_svg.py — draw the site map (lot + roads + contours) and the ground profile as SVG.

Inputs are the JSON files written by nsw_lot_terrain.py (or any equivalent):
  ring.json      [[lon,lat], ...]  closed lot boundary ring (WGS84)
  contours.json  [[elev_m, [[x_m,y_m], ...]], ...]  contour paths in local metres (origin = --lon/--lat)
  roads.json     [[name_or_attrs, hierarchy, [[lon,lat], ...]], ...]
Outputs (in --out-dir): site_svg.svg, profile_svg.svg, profile.json (street/W/E elevation, fall, gradient).

usage:
  python site_profile_svg.py --lon 152.0939 --lat -32.7396 --label "112A Salamander Way" --sublabel "908 m²" \
      [--ring ring.json --contours contours.json --roads roads.json] [--front-side auto|N] [--lang zh|en] [--out-dir .] [--force]

Strata guard: first queries NSW_Cadastre L9 at --lon/--lat; if the lot is a strata plan (lotidstring contains "SP", or hasstratum == 2)
it prints "strata lot (...): terrain is not meaningful for a unit, skipping (use --force to override)" and exits 0 without writing files.
Add --force to draw anyway. (The cadastre check fails open: offline or on a service error the script just carries on.)
Nothing here is address-specific: labels come from arguments, geometry from the JSON files.
"""
import sys, os, json, math, argparse, urllib.request, urllib.parse
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")

L = {"zh": {"entry": "入口:街面在高处,往下走", "entry_up": "入口:街面在低处,往上走", "legend": "棕线 = 官方等高线(米);绿块 = 地块边界",
            "scale": "20 米", "north": "北", "street": "街面中线", "front": "临街边界", "rear": "后边界", "xaxis": "离临街边界的距离(米,负值在街上)", "yaxis": "高程(米)",
            "site_aria": "地块、街道与等高线示意图", "prof_aria": "沿进深的地形剖面图"},
     "en": {"entry": "Entry: street is above, walk down", "entry_up": "Entry: street is below, walk up", "legend": "Brown = official contours (m); green = lot boundary",
            "scale": "20 m", "north": "N", "street": "Street centreline", "front": "Front boundary", "rear": "Rear boundary", "xaxis": "Distance from front boundary (m; negative = on the street)", "yaxis": "Elevation (m)",
            "site_aria": "Site map with roads and contours", "prof_aria": "Ground profile along the depth"}}

CAD = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer"

def strata_lot(lon, lat):
    """Cadastre lotidstring if the point is in a strata lot (SP plan or hasstratum == 2), else None. Fails open (None) on any error."""
    try:
        q = urllib.parse.urlencode({"f": "json", "geometry": "%f,%f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "lotidstring,hasstratum", "returnGeometry": "false"})
        r = json.loads(urllib.request.urlopen(urllib.request.Request(CAD + "/9/query?" + q, headers={"User-Agent": "Mozilla/5.0 auspptdd/0.2"}), timeout=60).read().decode("utf-8", "replace"))
        for f in r.get("features", []):
            at = f["attributes"]; lid = str(at.get("lotidstring") or "")
            if "SP" in lid.upper() or at.get("hasstratum") == 2: return lid
    except Exception as e: print("cadastre strata check failed (continuing):", repr(e)[:100], file=sys.stderr)
    return None

def seg_inter(p, q, a, b):
    x1, y1 = p; x2, y2 = q; x3, y3 = a; x4, y4 = b
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-12: return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
    return t if 0 <= t <= 1 and 0 <= u <= 1 else None

def dseg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p; dx, dy = bx - ax, by - ay; LL = dx * dx + dy * dy
    tt = 0 if LL == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / LL))
    return math.hypot(px - ax - tt * dx, py - ay - tt * dy)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lon", type=float, required=True); ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--label", default=""); ap.add_argument("--sublabel", default="")
    ap.add_argument("--ring", default="ring.json"); ap.add_argument("--contours", default="contours.json"); ap.add_argument("--roads", default="roads.json")
    ap.add_argument("--front-side", default="auto", help="index of the lot side facing the street, or auto (nearest road)")
    ap.add_argument("--lang", default="zh", choices=["zh", "en"]); ap.add_argument("--out-dir", default=".")
    ap.add_argument("--half", type=float, default=48, help="half-width of the site map in metres")
    ap.add_argument("--force", action="store_true", help="draw even if the point is in a strata lot (SP plan)")
    a = ap.parse_args(); T = L[a.lang]
    if not a.force:
        sl = strata_lot(a.lon, a.lat)
        if sl: print("strata lot (%s): terrain is not meaningful for a unit, skipping (use --force to override)" % sl); return
    K = 111320 * math.cos(math.radians(a.lat))
    xy = lambda p: ((p[0] - a.lon) * K, (p[1] - a.lat) * 111320)
    ring = json.load(open(a.ring, encoding="utf-8")); R = [xy(p) for p in ring]
    cont = json.load(open(a.contours, encoding="utf-8")) if os.path.exists(a.contours) else []
    roads = json.load(open(a.roads, encoding="utf-8")) if os.path.exists(a.roads) else []
    n = len(R) - 1; cx = sum(p[0] for p in R[:-1]) / n; cy = sum(p[1] for p in R[:-1]) / n
    # ---- front side
    road_pts = []
    for nm, hw, pts in roads:
        road_pts.append([xy(p) for p in pts])
    if a.front_side == "auto" and road_pts:
        best = None
        for i in range(n):
            mid = ((R[i][0] + R[i + 1][0]) / 2, (R[i][1] + R[i + 1][1]) / 2)
            d = min(dseg(mid, p, q) for pts in road_pts for p, q in zip(pts, pts[1:])) if any(len(p) > 1 for p in road_pts) else 1e9
            if best is None or d < best[0]: best = (d, i)
        fi = best[1]
    else:
        fi = int(a.front_side) if a.front_side != "auto" else 0
    mid = ((R[fi][0] + R[fi + 1][0]) / 2, (R[fi][1] + R[fi + 1][1]) / 2)
    # ---- site map
    X0, X1, Y0, Y1 = -a.half, a.half, -a.half * 0.83, a.half * 0.83; S = 6.5
    P = lambda x, y: ((x - X0) * S, (Y1 - y) * S); W, H = (X1 - X0) * S, (Y1 - Y0) * S
    o = ['<svg viewBox="0 0 %d %d" width="100%%" style="max-width:640px" role="img" aria-label="%s"><rect width="%d" height="%d" fill="#f4f1e8"/>' % (W, H, T["site_aria"], W, H),
         '<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8z" fill="#b42318"/></marker></defs>',
         '<clipPath id="cp"><rect width="%d" height="%d"/></clipPath><g clip-path="url(#cp)">' % (W, H)]
    labelled = set()
    def crop(path, m=6):  # keep only runs of points inside the view (+margin) so the SVG stays small
        runs, cur = [], []
        for x, y in path:
            if X0 - m <= x <= X1 + m and Y0 - m <= y <= Y1 + m: cur.append((x, y))
            elif cur: runs.append(cur); cur = []
        if cur: runs.append(cur)
        return [r for r in runs if len(r) > 1]
    cont = [(e, run) for e, path in cont for run in crop(path)]
    for e, path in sorted(cont, key=lambda c: c[0]):
        o.append('<polyline points="%s" fill="none" stroke="#b08a4a" stroke-width="%s" opacity=".8"/>' % (" ".join("%.1f,%.1f" % P(x, y) for x, y in path), "1.7" if e % 10 == 0 else "1"))
        if e not in labelled:
            inside = [(x, y) for x, y in path if X0 + 5 < x < X1 - 5 and Y0 + 4 < y < Y1 - 4]
            if inside:
                x, y = inside[len(inside) // 2]; px, py = P(x, y)
                o.append('<text x="%.1f" y="%.1f" font-size="11" fill="#8a6a2f" paint-order="stroke" stroke="#f4f1e8" stroke-width="3">%d</text>' % (px, py, e)); labelled.add(e)
    names = {}
    for (nm, hw, pts), pts2 in zip(roads, road_pts):
        nmtxt = nm if isinstance(nm, str) else (str(nm.get("roadnamebase", "")) + " " + str(nm.get("roadnametype", ""))).title()
        o.append('<polyline points="%s" fill="none" stroke="#fff" stroke-width="%d" stroke-linecap="round"/>' % (" ".join("%.1f,%.1f" % P(x, y) for x, y in pts2), int(6 * S)))
        o.append('<polyline points="%s" fill="none" stroke="#c9c5b8" stroke-width="1" stroke-dasharray="6 6"/>' % " ".join("%.1f,%.1f" % P(x, y) for x, y in pts2))
        m = pts2[len(pts2) // 2]
        if X0 < m[0] < X1 and Y0 < m[1] < Y1 and nmtxt not in names: names[nmtxt] = m
    for nmtxt, (x, y) in names.items():
        px, py = P(x, y); o.append('<text x="%.1f" y="%.1f" font-size="11.5" fill="#555" text-anchor="middle" paint-order="stroke" stroke="#fff" stroke-width="3">%s</text>' % (px, py, nmtxt))
    o.append('<polygon points="%s" fill="#1f6f54" fill-opacity=".28" stroke="#14342b" stroke-width="2.5"/>' % " ".join("%.1f,%.1f" % P(x, y) for x, y in R[:-1]))
    o.append('<text x="%.1f" y="%.1f" font-size="13" font-weight="700" fill="#14342b" text-anchor="middle">%s</text>' % (*P(cx, cy + 1.5), a.label))
    o.append('<text x="%.1f" y="%.1f" font-size="11" fill="#14342b" text-anchor="middle">%s</text>' % (*P(cx, cy - 2.5), a.sublabel))
    # ---- profile along front-mid -> centroid -> far
    far = (2 * cx - mid[0], 2 * cy - mid[1]); LL = math.dist(mid, far); ux, uy = (far[0] - mid[0]) / LL, (far[1] - mid[1]) / LL
    P0 = (mid[0] - ux * 14, mid[1] - uy * 14); P1 = (far[0] + ux * 14, far[1] + uy * 14); TL = math.dist(P0, P1); hits = []
    for e, path in cont:
        for s1, s2 in zip(path, path[1:]):
            tt = seg_inter(P0, P1, s1, s2)
            if tt is not None: hits.append((tt * TL - 14, e))
    hits.sort(); prof = hits
    def el(x):
        if not prof: return 0
        if x <= prof[0][0]: return prof[0][1]
        for (x1, e1), (x2, e2) in zip(prof, prof[1:]):
            if x1 <= x <= x2: return e1 + (e2 - e1) * (x - x1) / (x2 - x1) if x2 > x1 else e1
        return prof[-1][1]
    street_x = -7.5; s_el, w_el, e_el = el(street_x), el(0), el(LL); fall = w_el - e_el
    # entry arrow (direction from street into lot)
    ax_, ay_ = P(mid[0] - ux * 6, mid[1] - uy * 6); bx_, by_ = P(mid[0] + ux * 3, mid[1] + uy * 3)
    o.append('<path d="M%.1f,%.1f L%.1f,%.1f" stroke="#b42318" stroke-width="3" marker-end="url(#ah)"/>' % (ax_, ay_, bx_, by_))
    o.append('<text x="%.1f" y="%.1f" font-size="12" fill="#b42318" font-weight="700" text-anchor="middle">%s</text>' % (*P(mid[0] - ux * 10, mid[1] - uy * 10 - 3), T["entry"] if fall >= 0 else T["entry_up"]))
    o.append("</g>")
    sx, sy = P(X1 - 30, Y0 + 4); o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#1d2433" stroke-width="3"/><text x="%.1f" y="%.1f" font-size="11" fill="#1d2433">%s</text>' % (sx, sy, sx + 20 * S, sy, sx + 20 * S + 6, sy + 4, T["scale"]))
    nx, ny = P(X1 - 5, Y1 - 5); o.append('<path d="M%.1f,%.1f l0,-24 m0,0 l-5,9 m5,-9 l5,9" stroke="#1d2433" stroke-width="2" fill="none"/><text x="%.1f" y="%.1f" font-size="12" fill="#1d2433" text-anchor="middle">%s</text>' % (nx, ny + 20, nx, ny + 34, T["north"]))
    o.append('<text x="8" y="%d" font-size="11" fill="#8a6a2f">%s</text></svg>' % (H - 8, T["legend"]))
    os.makedirs(a.out_dir, exist_ok=True)
    open(os.path.join(a.out_dir, "site_svg.svg"), "w", encoding="utf-8").write("".join(o))
    # ---- profile svg
    if prof:
        PX0, PX1 = -12, LL + 10; E0 = math.floor(min(e for _, e in prof) / 2) * 2 - 2; E1 = math.ceil(max(e for _, e in prof) / 2) * 2 + 2
        sx_ = 10.0; sy_ = sx_ * 2.0
        Q = lambda x, e: (44 + (x - PX0) * sx_, 22 + (E1 - e) * sy_)
        Wp = 44 + (PX1 - PX0) * sx_ + 12; Hp = 22 + (E1 - E0) * sy_ + 48
        p = ['<svg viewBox="0 0 %d %d" width="100%%" style="max-width:720px" role="img" aria-label="%s">' % (Wp, Hp, T["prof_aria"])]
        for e in range(E0, E1 + 1, 2):
            x1, y1 = Q(PX0, e); x2, _ = Q(PX1, e); p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#eee"/><text x="38" y="%.1f" font-size="11" fill="#667085" text-anchor="end">%d</text>' % (x1, y1, x2, y1, y1 + 4, e))
        xs = [PX0 + i * 0.5 for i in range(int((PX1 - PX0) / 0.5) + 1)]
        ground = [Q(x, el(x)) for x in xs]; bx, by = Q(PX1, E0); ax0, ay0 = Q(PX0, E0)
        p.append('<polygon points="%s %.1f,%.1f %.1f,%.1f" fill="#d9c9a3"/>' % (" ".join("%.1f,%.1f" % g for g in ground), bx, by, ax0, ay0))
        p.append('<polyline points="%s" fill="none" stroke="#8a6a2f" stroke-width="2.5"/>' % " ".join("%.1f,%.1f" % g for g in ground))
        def vline(x, label, color="#1d2433"):
            X, Yg = Q(x, el(x)); _, Yt = Q(x, E1 - 0.4)
            p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-dasharray="4 4"/><text x="%.1f" y="%.1f" font-size="11.5" fill="%s" text-anchor="middle">%s</text><text x="%.1f" y="%.1f" font-size="11" fill="%s" text-anchor="middle">%.1f m</text>' % (X, Yt + 18, X, Yg, color, X, Yt, color, label, X, Yt + 13, color, el(x)))
        vline(street_x, T["street"], "#b42318"); vline(0, T["front"]); vline(LL, T["rear"])
        x0_, y0_ = Q(PX0, E0)
        for x in range(-10, int(PX1) + 1, 10):
            X, _ = Q(x, E0); p.append('<text x="%.1f" y="%.1f" font-size="11" fill="#667085" text-anchor="middle">%d</text>' % (X, y0_ + 14, x))
        p.append('<text x="%.1f" y="%.1f" font-size="11" fill="#667085" text-anchor="middle">%s</text>' % ((44 + Wp) / 2, y0_ + 30, T["xaxis"]))
        p.append('<text x="6" y="12" font-size="11" fill="#667085">%s</text></svg>' % T["yaxis"])
        open(os.path.join(a.out_dir, "profile_svg.svg"), "w", encoding="utf-8").write("".join(p))
    res = {"front_side": fi, "depth_m": round(LL, 1), "street": s_el, "front": w_el, "rear": e_el, "fall": round(fall, 2), "gradient_pct": round(fall / LL * 100, 1) if LL else None, "profile": [(round(x, 1), e) for x, e in prof]}
    json.dump(res, open(os.path.join(a.out_dir, "profile.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()
