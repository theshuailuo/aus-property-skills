// domain_building_profile.js - every SOLD record of one apartment building from its Domain "building profile" page.
//
// PURPOSE   Same-building sales history for a strata unit (price, date, beds / baths / cars per unit). It is the best free source for
//           NSW high-rise units: the NSW Valuer General sales layer keeps one latest sale per property and is sparse for strata, and
//           Aussie / REA / property.com.au block or rate-limit batch fetching of one building.
// WHERE TO RUN  Inside a real browser session that has the Domain building profile page open (the user's browser, or the agent's
//           in-app browser pane), via its JavaScript tool / DevTools console. It MUST run in the page: plain curl / scripts get HTTP 403,
//           and the sales are inside the page's cards, so the page text tool does not show them either.
//             1. Open  https://www.domain.com.au/building-profile/<address-slug>?filtertype=sold&pagesize=10&pageno=1
//                (find the slug from the unit's Domain property-profile page -> "Building profile" link; e.g. 12-example-street-sydney-nsw-2000).
//             2. Paste this whole file into the JS tool and run it. It fetches pageno=1..N (same origin, 5 pages at a time, stops at the first
//                empty page), parses each card with DOMParser and RETURNS ONE JSON TEXT (also logged to the console).
//             3. Save the returned text to  building.json  (the agent: write it to a file with the Write tool; a person: copy the
//                console output into a text file). The file is a JSON list:
//                  [{"unit":"1503","date":"2026-07-17","price":1270000,"kind":"sale","beds":2,"baths":2,"cars":1,"url":"..."}, ...]
//                price is null where Domain shows N/A (price withheld). date is ISO yyyy-mm-dd. kind is "rent?" when the price is under
//                $20,000 (the sold list also carries leased records priced per week): drop those. Lot numbers such as 24 or 28 with
//                no beds are car spaces / storage lots; beds null = not a dwelling.
//           Then:  nsw_comps_enrich.py --building-json building.json ...   and   unit_stack_svg.py --building-json building.json ...
// CARD RULE  A card = the smallest ancestor of an  a[href*="/property-profile/"]  link that holds only that one link. Its text nodes are joined
//           with spaces and matched with
//             (\$[\d.,]+[km]?|N/A)\s*(\d+[A-Z]?)/<house no> ... (\d{4})\s*([A-Z][a-z]{2})\s*(\d{1,2})      (price, unit, year, Mon, day)
//           with a second pattern for "17 Jul 2026". A card reads (checked Oct 2026):
//             "$1.27m | 1503/12 Example St | , | Sydney | NSW | 2000 | 2026 | Jul 17 | 2 | Beds | 2 | Baths | 1 | Parking"
//           beds / baths / cars come from the "N Beds", "N Baths", "N Parking" labels ("-" or a missing label = null). If Domain changes its
//           markup and nothing parses, the output is {"error":..., "sample":[card texts]} so the pattern can be fixed from a real card;
//           set DEBUG = true to see samples even on success.
// CAVEATS   Only what Domain publishes (sold filter, can start at off-the-plan settlements; price may be N/A). Be polite: one run per building.
//           Prices are shown in compact form ("$1.27m"), so they are rounded to about $10k; use them for ranges, not for exact comparisons.
//           Unit numbers are as Domain prints them; the house number is read from the URL slug unless HOUSE_NO is set below.

await (async function () {
  const HOUSE_NO = null;      // e.g. "150"; null = leading number of the building-profile slug in the current URL
  const PAGE_SIZE = 10, MAX_PAGES = 80, BATCH = 5, DEBUG = false;

  const m = location.pathname.match(/building-profile\/([^/?#]+)/);
  if (!m) return JSON.stringify({ error: "run this on a domain.com.au/building-profile/<slug> page", url: location.href });
  const slug = m[1];
  const house = (HOUSE_NO || (slug.match(/^(\d+[a-z]?)-/i) || [])[1] || "").toUpperCase();
  if (!house) return JSON.stringify({ error: "cannot read the house number from the slug; set HOUSE_NO", slug });
  const base = location.origin + "/building-profile/" + slug + "?filtertype=sold&pagesize=" + PAGE_SIZE + "&pageno=";

  const MON = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
  const iso = (y, mon, d) => y + "-" + String(MON[mon]).padStart(2, "0") + "-" + String(d).padStart(2, "0");
  const reA = new RegExp("(\\$[\\d.,]+[km]?|N/A)\\s*(\\d+[A-Z]?)/" + house + "\\b(.*?)(\\d{4})\\s*([A-Z][a-z]{2})\\s*(\\d{1,2})(?!\\d)");   // year Mon day
  const reB = new RegExp("(\\$[\\d.,]+[km]?|N/A)\\s*(\\d+[A-Z]?)/" + house + "\\b(.*?)(\\d{1,2})\\s*([A-Z][a-z]{2})\\s*(\\d{4})");            // day Mon year

  const money = s => {
    if (!s || /N\/A/i.test(s)) return null;
    const mult = /m$/i.test(s) ? 1e6 : /k$/i.test(s) ? 1e3 : 1;
    const v = parseFloat(s.replace(/[^0-9.]/g, "")) * mult;     // "$1,270,000" -> 1270000 ; "$1.27m" -> 1270000
    return isFinite(v) ? Math.round(v) : null;
  };
  const textOf = el => {
    const w = el.ownerDocument.createTreeWalker(el, NodeFilter.SHOW_TEXT), parts = [];
    for (let n = w.nextNode(); n; n = w.nextNode()) { const t = n.nodeValue.replace(/\s+/g, " ").trim(); if (t) parts.push(t); }
    return parts.join(" ");
  };
  const label = (txt, re) => { const x = re.exec(txt); return x && /^\d+$/.test(x[1]) ? +x[1] : null; };   // "2 Beds" -> 2 ; "- Beds" / absent -> null

  const rows = [], seen = new Set(), samples = [];
  async function page(n) {
    const r = await fetch(base + n, { credentials: "same-origin" });
    if (!r.ok) return { n, status: r.status, cards: [] };
    const doc = new DOMParser().parseFromString(await r.text(), "text/html"), byHref = new Map();
    for (const a of doc.querySelectorAll('a[href*="/property-profile/"]')) {
      const href = a.getAttribute("href"); let el = a, card = a;
      for (let i = 0; i < 8 && el.parentElement; i++) {          // smallest ancestor holding only this one property link
        el = el.parentElement;
        const hs = new Set([...el.querySelectorAll('a[href*="/property-profile/"]')].map(x => x.getAttribute("href")));
        if (hs.size > 1) break; card = el;
      }
      if (!byHref.has(href)) byHref.set(href, card);
    }
    return { n, status: r.status, cards: [...byHref].map(([href, card]) => ({ href, text: textOf(card) })) };
  }

  let stop = false, bad = 0;
  for (let p0 = 1; p0 <= MAX_PAGES && !stop; p0 += BATCH) {
    const res = await Promise.all(Array.from({ length: BATCH }, (_, i) => page(p0 + i).catch(e => ({ n: p0 + i, status: 0, cards: [], err: String(e) }))));
    for (const r of res.sort((a, b) => a.n - b.n)) {
      if (!r.cards.length) { stop = true; if (r.status && r.status !== 200) bad = r.status; continue; }
      const before = rows.length;
      for (const c of r.cards) {
        if (DEBUG && samples.length < 5) samples.push(c.text.slice(0, 300));
        let mt = reA.exec(c.text), y, mon, d;
        if (mt) { y = mt[4]; mon = mt[5]; d = mt[6]; } else if ((mt = reB.exec(c.text))) { d = mt[4]; mon = mt[5]; y = mt[6]; }
        if (!mt || !(mon in MON)) { if (samples.length < 5) samples.push(c.text.slice(0, 300)); continue; }
        const row = { unit: mt[2], date: iso(y, mon, d), price: money(mt[1]), kind: null, beds: label(c.text, /(\d+|[-–])\s*Beds?\b/i), baths: label(c.text, /(\d+|[-–])\s*Baths?\b/i),
                      cars: label(c.text, /(\d+|[-–])\s*(?:Parking|Car)/i), url: c.href.startsWith("http") ? c.href : location.origin + c.href };
        row.kind = row.price !== null && row.price < 20000 ? "rent?" : "sale";   // sold list sometimes carries leased records priced per week
        const key = row.unit + "|" + row.date + "|" + row.price;
        if (!seen.has(key)) { seen.add(key); rows.push(row); }
      }
      if (rows.length === before) stop = true;      // a page with nothing new (past the end, or the last page served again)
    }
  }
  rows.sort((a, b) => b.date.localeCompare(a.date) || a.unit.localeCompare(b.unit, undefined, { numeric: true }));
  if (!rows.length) return JSON.stringify({ error: bad ? "HTTP " + bad + " (blocked? run inside the logged-in browser tab)" : "no sold cards matched the pattern", slug, house, sample: samples });
  console.log("domain_building_profile: " + rows.length + " sold rows for " + slug);
  return JSON.stringify(DEBUG ? { rows, sample: samples } : rows);
})()
