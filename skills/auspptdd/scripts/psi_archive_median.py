#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
psi_archive_median.py — suburb house-sale median from a NSW Valuer General archived yearly PSI zip (1990–2000 format).

Download https://www.valuergeneral.nsw.gov.au/__psi/yearly/<YYYY>.zip in a browser (curl is blocked by the WAF) into an
EMPTY directory, then run with `python -I`. The .DAT is semicolon-separated, 'B' records are sales; this script finds the
suburb column by value and the price column as the most frequent plausible integer field, prints its guess and the median.
Check the printed sample rows against the VG format PDF before quoting the number.

usage: python -I psi_archive_median.py --zip ./dl/1996.zip --suburb "SALAMANDER BAY" [--min 30000 --max 5000000]
"""
import sys, zipfile, statistics, collections, argparse
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", required=True); ap.add_argument("--suburb", required=True)
    ap.add_argument("--min", type=int, default=30000); ap.add_argument("--max", type=int, default=5000000)
    a = ap.parse_args(); suburb = a.suburb.upper()
    z = zipfile.ZipFile(a.zip); names = [n for n in z.namelist() if n.upper().endswith(".DAT")]
    if not names: sys.exit("no .DAT in zip")
    rows = []
    for name in names:
        lines = z.read(name).decode("latin-1").splitlines()
        rows += [l.split(";") for l in lines if l.startswith("B;")]
    print("files", len(names), "B records", len(rows), "fields", len(rows[0]) if rows else 0)
    hits = [r for r in rows if any(f.strip().upper() == suburb for f in r)]
    print(suburb, "records", len(hits))
    for r in hits[:3]: print("  sample:", r)
    if not hits: return
    cand = collections.Counter()
    for r in hits:
        for i, f in enumerate(r):
            f = f.strip()
            if f.isdigit() and a.min <= int(f) <= a.max: cand[i] += 1
    idx = cand.most_common(1)[0][0]; print("price column guess: index", idx, "candidates", cand.most_common(4))
    prices = [int(r[idx]) for r in hits if r[idx].strip().isdigit() and a.min <= int(r[idx]) <= a.max]
    print("median", int(statistics.median(prices)), "n", len(prices), "(all records in the file for this suburb; strata flag not separated in this format — check the format PDF)")
if __name__ == "__main__":
    main()
