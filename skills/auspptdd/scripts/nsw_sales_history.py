#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nsw_sales_history.py — suburb house-sale history from the NSW Valuer General sales layer (SIX Valuation L1, 2001-).

Per year: all non-strata sales in the suburb (one query per year, 4-16 s each; run in the background).
With --strata the filter flips to strata<>0 (units/apartments) and the files are written as sales_hist_strata.json / market_growth_strata.json
so a house run and a unit run in the same folder do not overwrite each other.
Outputs sales_hist.json (raw rows per year) and market_growth.json:
  yearly {year: [median, n]}, growth rows for 5/10/20 years (+ "since 2001") using 3-year-window medians,
  last12 {n, median, latest, prices[]} for the price ruler, street_sales [] for the subject street.

usage:
  python nsw_sales_history.py --suburb "SALAMANDER BAY" [--street "SALAMANDER"] [--from 2001] [--out-dir .] [--strata]
Caveats (write them in the report): sale medians, not a repeat-sales index; the layer keeps the latest sale per property, so
early years are thinner. 30-year growth needs the VG yearly PSI zips (psi_archive_median.py) or a capital-city index.
STRATA WARNING: VG L1 keeps only the latest sale per property and strata coverage is sparse (North Sydney 2001-2019: 0-5 per year); for units
use the building's own sales history (Domain building profile) or suburb unit medians and state the basis in the report.
"""
import sys, os, json, time, argparse, datetime, statistics, urllib.request, urllib.parse
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 auspptdd/0.2"}
V = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/1/query"
def q(where):
    p = {"f": "json", "where": where, "outFields": "house_no,street,suburb,postcode,price,sale_date,area,strata,propid", "returnGeometry": "false"}
    req = urllib.request.Request(V + "?" + urllib.parse.urlencode(p), headers=UA)
    for attempt in range(3):
        try:
            t = time.time(); r = json.loads(urllib.request.urlopen(req, timeout=180).read().decode("utf-8", "replace"))
            if "error" in r: raise Exception(str(r["error"]))
            print("# %s -> %ds, %d rows" % (where, time.time() - t, len(r.get("features", []))), file=sys.stderr)
            return [f["attributes"] for f in r.get("features", [])]
        except Exception as e:
            print("retry", where, repr(e)[:80], file=sys.stderr); time.sleep(5)
    return []
STRATA_NOTE = ("VG L1 keeps only the latest sale per property and strata coverage is sparse (North Sydney 2001-2019: 0-5 per year); for units use the "
               "building's own sales history (Domain building profile) or suburb unit medians and state the basis in the report.")
def pd(s): return datetime.datetime.strptime(s, "%d %B %Y")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suburb", required=True); ap.add_argument("--street", help="subject street name (first word) for the same-street table")
    ap.add_argument("--from", dest="start", type=int, default=2001); ap.add_argument("--out-dir", default=".")
    ap.add_argument("--strata", action="store_true", help="query strata<>0 (units) instead of strata=0 (houses/land); sparse before ~2020, see the STRATA WARNING in --help")
    a = ap.parse_args(); sub = a.suburb.upper().replace("'", "''"); os.makedirs(a.out_dir, exist_ok=True)
    this_year = datetime.date.today().year; hist = {}; sfx = "_strata" if a.strata else ""; scond = "strata<>0" if a.strata else "strata=0"
    for y in range(a.start, this_year + 1):
        hist[str(y)] = q("suburb='%s' AND %s AND sale_date LIKE '%%%d'" % (sub, scond, y))
    json.dump(hist, open(os.path.join(a.out_dir, "sales_hist%s.json" % sfx), "w", encoding="utf-8"), ensure_ascii=False)
    yearly = {}
    for y, rows in hist.items():
        ps = [r["price"] for r in rows if r.get("price") and r["price"] > 100000]
        yearly[y] = [int(statistics.median(ps)) if ps else None, len(ps)]
    def win_median(y0, y1):
        ps = [r["price"] for y in range(y0, y1 + 1) for r in hist.get(str(y), []) if r.get("price") and r["price"] > 100000]
        return (int(statistics.median(ps)), len(ps)) if ps else (None, 0)
    cur_m, cur_n = win_median(this_year - 2, this_year); rows = []
    for yrs, label in [(5, "5"), (10, "10"), (20, "20")]:
        s_m, s_n = win_median(this_year - yrs - 2, this_year - yrs)
        if s_m and cur_m: rows.append({"period": "%s y" % label, "start": s_m, "start_n": s_n, "current": cur_m, "cum": round((cur_m / s_m - 1) * 100, 1), "ann": round(((cur_m / s_m) ** (1 / yrs) - 1) * 100, 2)})
    s_m, s_n = win_median(a.start, a.start + 2); span = this_year - 1 - a.start
    if s_m and cur_m and span > 20: rows.append({"period": "since %d (%d y)" % (a.start, span), "start": s_m, "start_n": s_n, "current": cur_m, "cum": round((cur_m / s_m - 1) * 100, 1), "ann": round(((cur_m / s_m) ** (1 / span) - 1) * 100, 2)})
    cutoff = datetime.datetime.today() - datetime.timedelta(days=365)
    last = [r for y in (str(this_year - 1), str(this_year)) for r in hist.get(y, []) if r.get("price") and r["price"] > 100000 and pd(r["sale_date"]) >= cutoff]
    prices = sorted(r["price"] for r in last)
    last12 = {"n": len(prices), "median": int(statistics.median(prices)) if prices else None, "latest": max((pd(r["sale_date"]) for r in last), default=None).strftime("%Y-%m-%d") if last else None, "window_label": "%s – %s" % (cutoff.strftime("%Y-%m-%d"), datetime.date.today().isoformat()), "prices": prices}
    street = []
    if a.street:
        for r in q("suburb='%s' AND street LIKE '%s%%'" % (sub, a.street.upper().replace("'", "''"))):
            street.append({"addr": "%s %s" % (r.get("house_no"), str(r.get("street", "")).title()), "price": r.get("price"), "date": r.get("sale_date"), "land": r.get("area"), "strata": r.get("strata")})
        street.sort(key=lambda r: pd(r["date"]), reverse=True)
    out = {"suburb": a.suburb, "current_window": [cur_m, cur_n], "yearly": yearly, "growth_rows": rows, "last12": last12, "street_sales": street,
           "scope": "strata (units)" if a.strata else "non-strata (houses/land)",
           "note": "VG sale medians (%s), 3-year windows; not a repeat-sales index. Layer keeps latest sale per property." % ("STRATA" if a.strata else "non-strata")}
    if a.strata: out["strata_warning"] = STRATA_NOTE
    json.dump(out, open(os.path.join(a.out_dir, "market_growth%s.json" % sfx), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for y, v in sorted(yearly.items()): print(y, v)
    print(json.dumps(rows, ensure_ascii=False)); print("last12", last12["n"], last12["median"]); print("written market_growth%s.json" % sfx)
    if a.strata: print("NOTE:", STRATA_NOTE)

if __name__ == "__main__":
    main()
