// node scripts/test_engine.js: the report engine must give the same numbers as holiday_calc.py
// (Lakes Entrance example inputs, today pinned to 2026-10-28). Exit 1 on any mismatch.
const HH = require('../templates/interactive/engine.js');
const base = {price: 575000, loan: 460000, rate: 0.068, rev0: 33516, peakVal: 196, offVal: 90, adr: 337, platformFee: 0.155, levy: 0, mgmtFee: 0.20,
  directCosts: 3500, fixedCosts: 5000 + 3500 + 5750 + 5000, landTax: 975, vrltEscalate: false, mtr: 0.45, years: 10, cpi: 0.025, sellPct: 0.025,
  otherCosts: 3000, furnishing: 30000, deposit: 0.045, index: 0.07, homeLoanRate: 0.065, bookNights: 21, bookNightly: 450, ltRent: 496,
  dwelling: 'established', own: {peak: 21, off: 0, peakBlocked: true, friends: 0}, state: 'VIC', vrlt: true, today: '2026-10-28', grossRent: 29400};
// expected: holiday_calc.py on the same inputs (after-tax cash last year, breakevens vs deposit / index / home loan)
const cases = [
  ['base', {}, 'red', -48249, [0.0717, 0.0787, 0.0815]],
  ['C', {grossRent: 32144, own: {peak: 7, off: 21, peakBlocked: false}}, 'green', -33276, [0.0527, 0.0608, 0.0641]],
  ['A', {own: {peak: 21, off: 7, peakBlocked: true}}, 'red', -42499, [0.0654, 0.0727, 0.0757]],
];
let bad = 0;
for (const [lab, over, zone, after, be] of cases) {
  const c = Object.assign({}, base, over), h = HH.holidayPath(c), b = HH.breakevens(c, h);
  const got = [b.deposit, b.index, b.mortgage].map(x => +x.toFixed(4));
  // the page's breakeven (wealth gap on the seven-path yardstick) must agree with breakevens()
  const page = ['dep', 'idx', 'mort'].map(k => +HH.solve(g => { const r = HH.paths(c, g).res; return r.you.W - r[k].W; }).toFixed(4));
  const ok = h.zone === zone && Math.round(h.m.afterLast) === after && got.join() === be.join() && page.join() === be.join();
  if (!ok) bad++;
  console.log(ok ? 'ok  ' : 'FAIL', lab, h.zone, Math.round(h.m.afterLast), got.join(' '), 'page', page.join(' '));
}
process.exit(bad ? 1 : 0);
