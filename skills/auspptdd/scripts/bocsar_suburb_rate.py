#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bocsar_suburb_rate.py — suburb crime counts from the BOCSAR open-data SuburbData.zip, WITH a state-wide baseline.

Download SuburbData.zip (about 13 MB; the CSV inside is about 440 MB) from the BOCSAR open-datasets page into an EMPTY,
separate directory, then run this script with `python -I`. The CSV is streamed, never loaded whole.
Columns: "Suburb","Offence category","Subcategory","Jan 1995", ... one column per month.

Output: counts for the last 12 months (or --from/--to) by offence category for the suburb, the state total over the same
months (sum of all suburbs), and per-1,000 rates for both when --pop / --state-pop are given.  A suburb number without the
state baseline is meaningless to a buyer — always show both.

usage:
  python -I bocsar_suburb_rate.py --zip ./dl/SuburbData.zip --suburb "Salamander Bay" --pop 4824 [--state-pop 8670105] [--from "Jul 2025" --to "Jun 2026"] [--out crime.json]
"""
import sys, csv, io, json, zipfile, argparse, collections
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", required=True); ap.add_argument("--suburb", required=True)
    ap.add_argument("--pop", type=float, help="suburb population (ABS QuickStats SAL)"); ap.add_argument("--state-pop", type=float, help="state population; omitted = fetched from ABS ERP_Q (latest quarter)")
    ap.add_argument("--state", default="NSW", help="NSW|VIC|QLD|SA|WA|TAS|NT|ACT (for the automatic ABS population fetch)")
    ap.add_argument("--from", dest="m0", help='first month, e.g. "Jul 2025" (default: last 12 available)'); ap.add_argument("--to", dest="m1")
    ap.add_argument("--out", default="crime.json")
    a = ap.parse_args()
    z = zipfile.ZipFile(a.zip); name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    f = io.TextIOWrapper(z.open(name), encoding="latin-1", newline="")
    rd = csv.reader(f); header = next(rd); months = header[3:]
    i1 = months.index(a.m1) if a.m1 else len(months) - 1
    i0 = months.index(a.m0) if a.m0 else max(0, i1 - 11)
    sel = list(range(i0, i1 + 1)); target = a.suburb.strip().lower()
    sub = collections.Counter(); state = collections.Counter(); sub_sub = collections.Counter(); nrows = 0
    for row in rd:
        nrows += 1
        if len(row) < 4: continue
        try: v = sum(int(row[3 + i] or 0) for i in sel)
        except ValueError: continue
        cat = row[1]; state[cat] += v
        if row[0].strip().lower() == target:
            sub[cat] += v; sub_sub[(cat, row[2])] += v
    tot_sub = sum(sub.values()); tot_state = sum(state.values())
    out = {"suburb": a.suburb, "window": "%s – %s" % (months[i0], months[i1]), "months": len(sel), "suburb_total": tot_sub, "suburb_by_category": dict(sub.most_common()),
           "suburb_by_subcategory": {"%s / %s" % k: v for k, v in sub_sub.most_common(12)}, "state_total": tot_state, "state_by_category": dict(state.most_common()),
           "source": "BOCSAR open data SuburbData.csv (%s), rows scanned %d" % (name, nrows)}
    if a.pop: out["suburb_per_1000"] = round(tot_sub / a.pop * 1000, 1)
    if not a.state_pop:
        try:
            import urllib.request
            code = {"NSW": 1, "VIC": 2, "QLD": 3, "SA": 4, "WA": 5, "TAS": 6, "NT": 7, "ACT": 8}[a.state.upper()]
            u = "https://data.api.abs.gov.au/rest/data/ABS,ERP_Q,1.0.0/1.3.TOT.%d.Q?lastNObservations=1&format=csvfilewithlabels" % code
            txt = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "ignore")
            hdr, row = [l.split(",") for l in txt.strip().splitlines()[:2]]
            a.state_pop = float(row[hdr.index("OBS_VALUE")]); out["state_pop_source"] = "ABS ERP_Q %s %s" % (a.state.upper(), row[hdr.index("TIME_PERIOD")])
            print("state population from ABS ERP_Q:", int(a.state_pop), row[hdr.index("TIME_PERIOD")], file=sys.stderr)
        except Exception as e:
            print("could not fetch state population from ABS:", e, "- pass --state-pop", file=sys.stderr)
    if a.state_pop: out["state_per_1000"] = round(tot_state / a.state_pop * 1000, 1)
    if a.pop and a.state_pop and out["state_per_1000"]: out["ratio_suburb_to_state"] = round(out["suburb_per_1000"] / out["state_per_1000"], 2)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("state_by_category", "suburb_by_subcategory")}, ensure_ascii=False, indent=1)); print("written", a.out)
if __name__ == "__main__":
    main()
