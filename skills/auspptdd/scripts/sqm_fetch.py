#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sqm_fetch.py — SQM Research free pages (postcode scope): vacancy, stock on market, asking prices, asking rents.

The numbers sit in each page's source as `var data = [...]`; a browser User-Agent is enough (no login).
Writes sqm.json with: vacancy rows [y,m,pct,vacant,total], som rows [y,m,houses,units],
ask rows  [date, houses_all, houses_3, units_all, units_2]   (asking price, AUD)
rent rows [date, houses_all, houses_3, units_all, units_2]   (asking rent, AUD per week)
plus 12-month vacancy average and 3-years-ago comparisons.
Series order (checked on postcode 2060 and 6004, Oct 2026): each asking-price / weekly-rent page carries one `var data` array of objects
{date, houses_all, houses_3, units_all, units_2, combined} (the chart plots them as All Houses, 3 Bed Houses, All Units, 2 Bed Units, Combined).
If a page ever ships the units series in a second `var data` block, the blocks are merged by date. Asking prices are medians of current
listings, so thin postcodes jump around; units_2 = 2-bedroom units only. A column is null where SQM has no value for that date.
Scope is POSTCODE, not suburb — say so in the report.

usage: python sqm_fetch.py --postcode 2100 [--out sqm.json]
"""
import sys, re, json, argparse, urllib.request
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64) Chrome/124", "Accept-Language": "en-AU,en;q=0.9"}
PAGES = {"vacancy": "https://sqmresearch.com.au/graph_vacancy.php?postcode=%s&t=1",
         "som": "https://sqmresearch.com.au/property/total-property-listings?postcode=%s&t=1&hu=1",
         "ask": "https://sqmresearch.com.au/asking-property-prices.php?postcode=%s&t=1",
         "rent": "https://sqmresearch.com.au/weekly-rents.php?postcode=%s&t=1"}
def fetch(url):
    h = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
    blocks = []
    for m in re.finditer(r"var\s+data\s*=\s*(\[.*?\]);", h, re.S):
        try: blocks.append(json.loads(m.group(1)))
        except ValueError: pass
    if len(blocks) <= 1: return blocks[0] if blocks else []
    merged = {}  # several `var data` blocks (e.g. houses block + units block): merge row dicts by date / (year, month)
    for b in blocks:
        for r in b: merged.setdefault(r.get("date") or (r.get("year"), r.get("month")), {}).update(r)
    return list(merged.values())
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--postcode", required=True); ap.add_argument("--out", default="sqm.json")
    a = ap.parse_args(); out = {"postcode": a.postcode}
    for k, u in PAGES.items():
        try: out[k + "_raw"] = fetch(u % a.postcode); print(k, len(out[k + "_raw"]), "rows", file=sys.stderr)
        except Exception as e: out[k + "_raw"] = []; print(k, "failed", repr(e)[:100], file=sys.stderr)
    vac = [[r["year"], r["month"], round(float(r["vr"]) * 100, 2), r.get("listings"), r.get("properties")] for r in out["vacancy_raw"]]
    som = [[r["year"], r["month"], r.get("houses"), r.get("units")] for r in out["som_raw"]]
    cols = lambda r: [r["date"], r.get("houses_all"), r.get("houses_3"), r.get("units_all"), r.get("units_2")]
    ask = [cols(r) for r in out["ask_raw"]]
    rent = [cols(r) for r in out["rent_raw"]]
    out.update({"vacancy": {"scope": "postcode %s" % a.postcode, "rows": vac[-36:], "avg12": round(sum(r[2] for r in vac[-12:]) / 12, 2) if len(vac) >= 12 else None, "three_years_ago": vac[-37] if len(vac) > 37 else None},
                "som": {"rows": som[-36:], "three_years_ago": som[-37] if len(som) > 37 else None},
                "ask": ask[-26:], "ask_one_year_ago": ask[-53:-51] if len(ask) > 53 else [], "rent": rent[-8:],
                "columns": {"ask": ["date", "houses_all", "houses_3", "units_all", "units_2"], "rent": ["date", "houses_all", "houses_3", "units_all", "units_2"]}})
    for k in list(out):
        if k.endswith("_raw"): del out[k]
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("vacancy latest", vac[-1] if vac else None, "| avg12", out["vacancy"]["avg12"], "| som latest", som[-1] if som else None, "| ask latest", ask[-1] if ask else None)
    print("written", a.out)
if __name__ == "__main__":
    main()
