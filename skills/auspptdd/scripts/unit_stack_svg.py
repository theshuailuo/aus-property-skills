#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unit_stack_svg.py — two strata-substitute charts from a building's own sales history (the unit equivalent of the land/slope charts).

Purpose  For a unit, "the same stack" and "the same bedrooms in the same building" are the closest comparables there are. Draws
           stack_svg.svg     price of sales in the subject's stack (same last-two digits of the unit number, e.g. 1803 -> xx03) x level
           building_svg.svg  all sales of units with the subject's bedroom count x sale date, with an optional fair-range band, an
                             optional guide-price line and the subject's own previous sale highlighted
Inputs   --building-json  list of {unit, date, price, beds, baths, cars[, kind]} as written by domain_building_profile.js
                          (rows with price null, kind "rent?" or price < 100,000 are ignored; date is yyyy-mm-dd or yyyy-mm)
         --house-no       building street number, used in the chart title (and to ignore rows whose "address" names another number)
         --subject-unit   e.g. 1803 (level = unit number without its last two digits = 18; verify that the building numbers this way)
         --beds           subject bedroom count (rows with a different beds value are dropped; rows with beds missing are kept)
         --range-lo/--range-hi  fair-value band drawn on building_svg (AUD, optional)      --guide  guide / asking price (AUD, optional)
         --building-label  optional building name for the title     --max-price  drop sales above this (e.g. special layouts, default:
         none, but sales above 2.5 x the median are dropped and counted in the title)       --recent-years  sales newer than this are green (default 2)
         --lang zh|en   --out-dir .
Outputs  stack_svg.svg, building_svg.svg in --out-dir (plain SVG, currentColor text so it follows the page theme).
Caveats  Levels come from the unit number, not from a floor plan. Prices are what the source shows (Domain rounds to ~$10k). Sales
         at the peak of a launch (settlements of off-the-plan units) sit far from today: look at the dates before using the band.
"""
import sys, os, json, argparse, statistics, datetime as dt
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")

T = {"zh": {"t1": "同一竖列(xx%s 户型)成交价 × 楼层 · %s", "t2": "楼内%s房成交价 × 日期(%s–%s,n=%d%s)", "level": "楼层(Level)", "guide": "指导价 %s",
            "last": "%s 上次成交 %s(%s)", "foot1": "绿 = %s 年内成交;灰 = 更早。来源:楼栋成交记录,价格为成交价", "band": "公允区间 %s–%s",
            "foot2": "红 = 标的 %s;绿 = 同竖列;蓝 = 楼内其他同房型。来源:楼栋成交记录", "excl": ";已剔除 %d 笔偏离过大", "nodata": "无数据"},
     "en": {"t1": "Same stack (xx%s) sale price by level · %s", "t2": "%s-bed sales in the building by date (%s–%s, n=%d%s)", "level": "Level", "guide": "Guide %s",
            "last": "%s previous sale %s (%s)", "foot1": "Green = sold within %s yr; grey = earlier. Source: the building's own sales records (sold prices)",
            "band": "Fair range %s–%s", "foot2": "Red = subject %s; green = same stack; blue = other units of the same size. Source: the building's own sales records",
            "excl": "; %d outlier(s) dropped", "nodata": "No data"}}

def pdate(s):
    s = str(s)
    if len(s) == 7: s += "-01"
    return dt.date.fromisoformat(s[:10])

def money(p):
    return "$%.2fM" % (p / 1e6) if p >= 1e6 else "$%dk" % round(p / 1e3)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--building-json", required=True); ap.add_argument("--house-no", required=True); ap.add_argument("--subject-unit", required=True)
    ap.add_argument("--beds", type=int, required=True); ap.add_argument("--range-lo", type=float); ap.add_argument("--range-hi", type=float)
    ap.add_argument("--guide", type=float); ap.add_argument("--building-label", default=""); ap.add_argument("--max-price", type=float)
    ap.add_argument("--recent-years", type=float, default=2); ap.add_argument("--lang", default="zh", choices=["zh", "en"]); ap.add_argument("--out-dir", default=".")
    a = ap.parse_args(); L = T[a.lang]; os.makedirs(a.out_dir, exist_ok=True)
    rows = json.load(open(a.building_json, encoding="utf-8"))
    house = str(a.house_no).upper(); subj = str(a.subject_unit).upper()
    def ok(r):
        if r.get("price") is None or r["price"] < 100000 or r.get("kind") == "rent?" or not r.get("date"): return False
        if r.get("beds") not in (None, a.beds): return False
        addr = str(r.get("address", "")).upper()
        return not ("/" in addr and not addr.split("/")[1].split()[0] == house)
    base = [dict(r, _d=pdate(r["date"]), _u=str(r["unit"]).upper()) for r in rows if ok(r)]
    if not base: print(L["nodata"]); sys.exit(1)
    med = statistics.median(r["price"] for r in base)
    cap = a.max_price or 2.5 * med
    pts = [r for r in base if r["price"] <= cap]; dropped = len(base) - len(pts)
    lvl = lambda u: int(u[:-2]) if u[:-2].isdigit() else None
    suffix = subj[-2:]; label = ("%s %s" % (a.building_label, a.house_no)).strip()
    sub_sales = sorted([r for r in base if r["_u"] == subj], key=lambda r: r["_d"])
    last_sub = sub_sales[-1] if sub_sales else None
    latest = max(r["_d"] for r in pts); recent_cut = latest - dt.timedelta(days=365.25 * a.recent_years)

    # ---- chart 1: same stack x level
    stack = sorted([(lvl(r["_u"]), r) for r in pts if r["_u"][-2:] == suffix and r["_u"] != subj and lvl(r["_u"]) is not None], key=lambda t: t[0])  # subject's own sale is drawn separately
    sl = lvl(subj)
    W, H, Lm, R, Tm, B = 640, 300, 60, 20, 30, 40
    vals = [r["price"] for _, r in stack] + [v for v in (a.guide, last_sub["price"] if last_sub else None) if v]
    if not vals: vals = [med]
    ymin = (min(vals) // 100000 - 1) * 100000; ymax = (max(vals) // 100000 + 2) * 100000
    lvs = [l for l, _ in stack] + ([sl] if sl else []); lv_min, lv_max = min(lvs) - 1, max(lvs) + 1
    X = lambda v: Lm + (v - lv_min) / (lv_max - lv_min) * (W - Lm - R)
    Y = lambda p: Tm + (ymax - p) / (ymax - ymin) * (H - Tm - B)
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="100%%" style="max-width:%dpx;font-family:system-ui,sans-serif;font-size:11px">' % (W, H, W)]
    s.append('<text x="%d" y="16" font-size="13" font-weight="600" fill="currentColor">%s</text>' % (Lm, L["t1"] % (suffix, label)))
    step = 100000 if ymax - ymin <= 700000 else 200000
    for p in range(int(ymin), int(ymax) + 1, step):
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="currentColor" stroke-opacity="0.15"/><text x="%d" y="%.1f" text-anchor="end" fill="currentColor" opacity="0.7">$%.1fM</text>' % (Lm, W - R, Y(p), Y(p), Lm - 6, Y(p) + 4, p / 1e6))
    for v in range(int(lv_min) + 1, int(lv_max), 2 if lv_max - lv_min > 10 else 1):
        s.append('<text x="%.1f" y="%d" text-anchor="middle" fill="currentColor" opacity="0.7">L%d</text>' % (X(v), H - B + 14, v))
    s.append('<text x="%d" y="%d" text-anchor="middle" fill="currentColor" opacity="0.7">%s</text>' % ((Lm + W - R) / 2, H - 6, L["level"]))
    for v, r in stack:
        recent = r["_d"] >= recent_cut
        s.append('<circle cx="%.1f" cy="%.1f" r="6" fill="%s" fill-opacity="0.85"/>' % (X(v), Y(r["price"]), "#2a7f62" if recent else "#9aa"))
        s.append('<text x="%.1f" y="%.1f" fill="currentColor">%s %s %s</text>' % (X(v) + 8, Y(r["price"]) - 6, r["_u"], money(r["price"]), str(r["date"])[:7]))
    if sl:
        if a.guide:
            s.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#c0392b"/>' % (X(sl), Y(a.guide) - 9, X(sl) + 8, Y(a.guide) + 5, X(sl) - 8, Y(a.guide) + 5))
            s.append('<text x="%.1f" y="%.1f" fill="#c0392b" font-weight="600">%s %s</text>' % (X(sl) + 10, Y(a.guide) + 4, subj, L["guide"] % money(a.guide)))
        if last_sub:
            s.append('<circle cx="%.1f" cy="%.1f" r="5" fill="none" stroke="#c0392b" stroke-width="2"/>' % (X(sl), Y(last_sub["price"])))
            s.append('<text x="%.1f" y="%.1f" fill="#c0392b">%s</text>' % (X(sl) + 10, Y(last_sub["price"]) + 4, L["last"] % (subj, money(last_sub["price"]), str(last_sub["date"])[:7])))
    s.append('<text x="%d" y="%d" text-anchor="end" fill="currentColor" opacity="0.6">%s</text>' % (W - R, H - B + 28, L["foot1"] % ("%g" % a.recent_years)))
    s.append("</svg>")
    open(os.path.join(a.out_dir, "stack_svg.svg"), "w", encoding="utf-8").write("\n".join(s))

    # ---- chart 2: all same-beds sales x date
    d0 = dt.date(min(r["_d"] for r in pts).year, 1, 1); d1 = dt.date(latest.year + 1, 1, 1)
    lo_v = [r["price"] for r in pts] + [v for v in (a.guide, a.range_lo, a.range_hi) if v]
    ymin = (min(lo_v) // 100000 - 1) * 100000; ymax = (max(lo_v) // 100000 + 2) * 100000
    X = lambda d: Lm + (d - d0).days / (d1 - d0).days * (W - Lm - R)
    Y = lambda p: Tm + (ymax - p) / (ymax - ymin) * (H - Tm - B)
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="100%%" style="max-width:%dpx;font-family:system-ui,sans-serif;font-size:11px">' % (W, H, W)]
    s.append('<text x="%d" y="16" font-size="13" font-weight="600" fill="currentColor">%s</text>' % (Lm, L["t2"] % (a.beds, d0.year, latest.year, len(pts), L["excl"] % dropped if dropped else "")))
    step = 100000 if ymax - ymin <= 700000 else 200000 if ymax - ymin <= 1500000 else 500000
    for p in range(int(ymin), int(ymax) + 1, step):
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="currentColor" stroke-opacity="0.15"/><text x="%d" y="%.1f" text-anchor="end" fill="currentColor" opacity="0.7">$%.1fM</text>' % (Lm, W - R, Y(p), Y(p), Lm - 6, Y(p) + 4, p / 1e6))
    ystep = 1 if d1.year - d0.year <= 12 else 2
    for yr in range(d0.year, d1.year, ystep):
        s.append('<text x="%.1f" y="%d" text-anchor="middle" fill="currentColor" opacity="0.7">%d</text>' % (X(dt.date(yr, 7, 1)), H - B + 14, yr))
    if a.range_lo and a.range_hi:
        s.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="#2a7f62" fill-opacity="0.12"/>' % (Lm, Y(a.range_hi), W - Lm - R, Y(a.range_lo) - Y(a.range_hi)))
        s.append('<text x="%d" y="%.1f" text-anchor="end" fill="#2a7f62">%s</text>' % (W - R - 4, Y(a.range_hi) - 4, L["band"] % (money(a.range_lo), money(a.range_hi))))
    for r in sorted(pts, key=lambda r: r["_d"]):
        is_sub = r["_u"] == subj; stk = r["_u"][-2:] == suffix
        s.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="%s" fill-opacity="0.85"/>' % (X(r["_d"]), Y(r["price"]), 6 if is_sub else 4, "#c0392b" if is_sub else ("#2a7f62" if stk else "#5b7fa6")))
        if is_sub or stk: s.append('<text x="%.1f" y="%.1f" fill="currentColor" font-size="10">%s</text>' % (X(r["_d"]) + 6, Y(r["price"]) - 5, r["_u"]))
    if a.guide:
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#c0392b" stroke-dasharray="4 3"/><text x="%d" y="%.1f" fill="#c0392b">%s</text>' % (Lm, W - R, Y(a.guide), Y(a.guide), Lm + 4, Y(a.guide) - 4, L["guide"] % money(a.guide)))
    s.append('<text x="%d" y="%d" text-anchor="end" fill="currentColor" opacity="0.6">%s</text>' % (W - R, H - B + 28, L["foot2"] % subj))
    s.append("</svg>")
    open(os.path.join(a.out_dir, "building_svg.svg"), "w", encoding="utf-8").write("\n".join(s))
    print("stack points", len(stack), "| same-beds points", len(pts), "| dropped", dropped, "| subject sales", len(sub_sales), "| written stack_svg.svg, building_svg.svg in", a.out_dir)

if __name__ == "__main__":
    main()
