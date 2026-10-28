// JS port of holiday-home holiday_calc.py (buy mode) + seven-path comparison on one yardstick.
// Same income and tax formulas as the Python script; c.today pins "today" so results are reproducible.
(function (root) {
  const REFORM = new Date('2027-07-01T00:00:00');
  // years from "today" to 1 July 2027 (losses quarantined and new CGT rules after that)
  const preYears = c => Math.max(0, (REFORM - new Date((c.today || new Date().toISOString().slice(0, 10)) + 'T00:00:00')) / 86400000 / 365.25);

  // general transfer duty, same tables as holiday_calc.py (verified 2026-10-23); other states: c.duty or c.dutyRate
  const DUTY = {
    NSW: [[0, 0, 0.0125], [18000, 225, 0.015], [38000, 525, 0.0175], [103000, 1662, 0.035], [387000, 11602, 0.045], [1290000, 52237, 0.055]],
    QLD: [[5000, 0, 0.015], [75000, 1050, 0.035], [540000, 17325, 0.045], [1000000, 38025, 0.0575]],
  };
  function stateDuty(c, v) {
    if (c.state === 'VIC' || !c.state) return vicDuty(v);
    const t = DUTY[c.state];
    if (!t) return v * (c.dutyRate != null ? c.dutyRate : 0.04);
    if (c.state === 'QLD' && v <= 5000) return 0;
    let [f, b, r] = t[0]; t.forEach(([f2, b2, r2]) => { if (v > f2) { f = f2; b = b2; r = r2; } });
    return b + (v - f) * r;
  }

  function vicDuty(v) {
    if (v <= 25000) return v * 0.014;
    if (v <= 130000) return 350 + (v - 25000) * 0.024;
    if (v <= 960000) return 2870 + (v - 130000) * 0.06;
    if (v <= 2000000) return v * 0.055;
    return 110000 + (v - 2000000) * 0.065;
  }

  function atoScreen(u) {
    if (u.peakBlocked || u.refuses || u.commercial === false) return 'red';
    if (u.peak > 7 || u.off > 28 || (u.friends || 0) > 0) return 'amber';
    return 'green';
  }

  const quarantined = (c, t) => c.dwelling !== 'new_build' && (t - 1) >= preYears(c);

  function taxSeries(c, taxable) {
    let pool = 0; const taxes = [];
    taxable.forEach((ti, i) => {
      const t = i + 1;
      if (ti < 0 && quarantined(c, t)) { pool += -ti; taxes.push(0); }
      else if (ti > 0 && pool > 0) { const used = Math.min(pool, ti); pool -= used; taxes.push((ti - used) * c.mtr); }
      else taxes.push(ti * c.mtr);
    });
    return { taxes, pool };
  }

  // land tax per year t (1-based): general land tax + VIC vacant residential land tax when c.vrlt is on
  // (1%, 2%, 3% of CIV for consecutive years; holiday-home exemption from 28 nights' own use; 183 occupied nights also clears it)
  function landTaxYear(c, t, ownNights, rented) {
    let lt = c.landTax;
    const vacant = c.vrlt && rented ? ownNights < 28 && c._guestNights < 183 : false;
    if (vacant) {
      const rate = c.vrltEscalate ? Math.min(0.01 * t, 0.03) : 0.01;
      lt += c.price * rate;
    }
    return lt;
  }

  function strModel(c, zone) {
    const u = c.own;
    const own = u.peak + u.off + (u.friends || 0);
    const rev = c.grossRent != null ? c.grossRent : Math.max(0, c.rev0 - u.peak * c.peakVal - u.off * c.offVal);
    const plat = rev * c.platformFee;
    const levy = rev * (c.levy || 0);
    const mgmt = (rev - plat) * c.mgmtFee;
    const direct = c.directCosts;
    const interest = c.loan * c.rate;
    const share = zone === 'red' ? 0 : Math.max(0, (365 - own) / 365);
    c = Object.assign({}, c, { _guestNights: rev / c.adr });
    const n = c.years; const rows = [];
    for (let t = 1; t <= n; t++) {
      const hold = c.fixedCosts + landTaxYear(c, t, own, true);
      const preTax = rev - levy - plat - mgmt - direct - hold - interest;
      const ded = levy + plat + mgmt + direct + (hold + interest) * share;
      rows.push({ hold, preTax, taxable: rev - ded, denied: (hold + interest) * (1 - share) });
    }
    const { taxes, pool } = taxSeries(c, rows.map(r => r.taxable));
    const after = rows.map((r, i) => r.preTax - taxes[i]);
    const last = rows[n - 1];
    return {
      rev, plat, levy, mgmt, direct, interest, hold: last.hold, preTax: last.preTax, tax: taxes[n - 1],
      after, afterLast: after[n - 1], afterFirst: after[0], pool,
      denied: rows.reduce((s, r) => s + r.denied, 0), share, own,
    };
  }

  function ltModel(c, lt) {
    const rev = lt.weeklyRent * (52 - lt.vacancyWeeks);
    const mgmt = rev * lt.mgmtFee;
    const hold = lt.fixedCosts + lt.landTax;
    const interest = c.loan * c.rate;
    const preTax = rev - mgmt - hold - interest;
    const { taxes, pool } = taxSeries(c, Array(c.years).fill(preTax));
    const after = taxes.map(tx => preTax - tx);
    return { rev, mgmt, hold, interest, preTax, after, afterLast: after[c.years - 1], pool };
  }

  function cgt(c, sale, costBase, n, g) {
    const mtr = c.mtr, PRE = preYears(c);
    if (n <= PRE) return Math.max(0, sale - costBase) * 0.5 * mtr;
    let v1 = c.price * Math.pow(1 + g, PRE);
    v1 = PRE > 0 ? Math.max(v1, costBase) : costBase;
    const preTax = Math.max(0, v1 - costBase) * 0.5 * mtr;
    const indexed = Math.max(v1, costBase) * Math.pow(1 + c.cpi, n - PRE);
    return preTax + Math.max(0, sale - indexed) * Math.max(mtr, 0.30);
  }

  function exitValue(c, g, costBase, deniedTotal, pool) {
    const n = c.years;
    const sale = c.price * Math.pow(1 + g, n);
    const sellCost = sale * c.sellPct;
    let tax = cgt(c, sale, costBase + deniedTotal + sellCost, n, g);
    tax = Math.max(0, tax - pool * c.mtr);
    return sale - sellCost - c.loan - tax;
  }

  const fv = (flows, r) => flows.reduce((s, x, i) => s + x * Math.pow(1 + r, flows.length - (i + 1)), 0);

  function solve(fn, lo = -0.10, hi = 0.30) {
    if (fn(lo) >= 0) return lo;
    if (fn(hi) < 0) return null;
    for (let i = 0; i < 80; i++) { const mid = (lo + hi) / 2; if (fn(mid) >= 0) hi = mid; else lo = mid; }
    return (lo + hi) / 2;
  }

  function altRates(c) {
    return { deposit: c.deposit * (1 - c.mtr), index: c.index * (1 - c.mtr * 0.5), mortgage: c.homeLoanRate };
  }

  // booking: holiday nights not covered by own use are booked
  const bookCost = (c, ownNights) => Math.max(0, c.bookNights - ownNights) * c.bookNightly;

  function holidayPath(c) {
    const zone = atoScreen(c.own);
    const m = strModel(c, zone);
    const duty = c.duty != null ? c.duty : stateDuty(c, c.price);
    const upfront = c.price - c.loan + duty + c.otherCosts + c.furnishing;
    const costBase = c.price + duty + c.otherCosts;
    const book = bookCost(c, m.own);
    const outflows = m.after.map(a => -a + book);   // money the family puts in each year
    const exitAt = g => exitValue(c, g, costBase, m.denied, m.pool);
    return { zone, m, duty, upfront, costBase, book, outflows, exitAt };
  }

  // breakeven vs each alternative, same as holiday_calc.py: the lump sum earns the alternative's rate,
  // money put in or saved each year is counted at the after-tax deposit rate (one yardstick, as in paths())
  function breakevens(c, h) {
    const out = {}; const n = c.years; const allBook = c.bookNights * c.bookNightly; const rd = altRates(c).deposit;
    for (const [k, r] of Object.entries(altRates(c))) {
      const other = h.upfront * Math.pow(1 + r, n) + fv(h.outflows.map(x => x - allBook), rd);
      out[k] = solve(g => h.exitAt(g) - other);
    }
    return out;
  }

  // ---- all paths on one yardstick: wealth at year n = assets - FV(outflows at after-tax deposit rate)
  function paths(c, g) {
    const n = c.years, r = altRates(c), rd = r.deposit;
    const allBook = c.bookNights * c.bookNightly;
    const res = {};
    const mk = (key, label, kind, h) => {
      const W = h.exitAt(g) + (C0v - h.upfront) * Math.pow(1 + rd, n) - fv(h.outflows, rd);
      res[key] = { label, kind, W, cashYear: avg(h.outflows), zone: h.zone, h };
    };
    const avg = a => a.reduce((s, x) => s + x, 0) / a.length;
    const hYou = holidayPath(c);
    const C0v = hYou.upfront;
    mk('you', '度假屋 · 你设定的用法', 'hh', hYou);
    const oo = c.optOwn || { peak: 7, off: 21 };
    const cOpt = Object.assign({}, c, { own: { peak: oo.peak, off: oo.off, peakBlocked: false, friends: 0 } });
    mk('opt', '度假屋 · 最优排法', 'hh', holidayPath(cOpt));
    const cNone = Object.assign({}, c, { own: { peak: 0, off: 0, peakBlocked: false, friends: 0 } });
    mk('rent', '度假屋 · 只出租不自用', 'hh', holidayPath(cNone));
    // long-term rental in the same town, holidays booked
    const ltCfg = { weeklyRent: c.ltRent, vacancyWeeks: c.ltVacancyWeeks != null ? c.ltVacancyWeeks : 2, mgmtFee: c.ltMgmtFee != null ? c.ltMgmtFee : 0.07,
      fixedCosts: c.price * (c.ltFixedPct != null ? c.ltFixedPct : 0.012), landTax: c.landTax };
    const lt = ltModel(c, ltCfg);
    const dutyLt = stateDuty(c, c.price);
    const upLt = c.price - c.loan + dutyLt + c.otherCosts;
    const exitLt = gg => exitValue(c, gg, c.price + dutyLt + c.otherCosts, 0, lt.pool);
    const ltOut = lt.after.map(a => -a + allBook);
    res.lt = { label: '买当地长租房 + 度假订房', kind: 'lt', W: exitLt(g) + (C0v - upLt) * Math.pow(1 + rd, n) - fv(ltOut, rd), cashYear: avg(ltOut), lt, upLt, exitLt, ltOut };
    const bookFlows = Array(n).fill(allBook);
    res.dep = { label: '不买房 · 存定期 + 订房', kind: 'alt', W: C0v * Math.pow(1 + rd, n) - fv(bookFlows, rd), cashYear: allBook };
    res.idx = { label: '不买房 · 指数基金 + 订房', kind: 'alt', W: C0v * Math.pow(1 + r.index, n) - fv(bookFlows, rd), cashYear: allBook };
    res.mort = { label: '不买房 · 提前还房贷 + 订房', kind: 'alt', W: C0v * Math.pow(1 + r.mortgage, n) - fv(bookFlows, rd), cashYear: allBook };
    return { res, C0: C0v, hYou, cOpt };
  }

  // same comparison but read at many growth rates (for the line chart)
  function wealthCurve(c, key, gs) { return gs.map(g => paths(c, g).res[key].W); }

  const api = { preYears, stateDuty, vicDuty, atoScreen, strModel, ltModel, exitValue, holidayPath, breakevens, paths, wealthCurve, altRates, solve, fv };
  if (typeof module !== 'undefined') module.exports = api; else root.HH = api;
})(this);
