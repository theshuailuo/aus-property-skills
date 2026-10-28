
// All case data comes from the <script type="application/json" id="case"> block that build_report.py writes.
const CASE = JSON.parse(document.getElementById('case').textContent);
const D0 = CASE.defaults, M = CASE.model, TX = CASE.text;
const G1 = CASE.growthRefs[0].g, G2 = CASE.growthRefs[1].g;
let S = JSON.parse(JSON.stringify(D0));
const $ = id => document.getElementById(id);
const fmt = (x, sign) => (x < 0 ? '−' : (sign && x > 0 ? '+' : '')) + 'A$' + Math.abs(Math.round(x)).toLocaleString('en-AU');
const wan = x => (x < 0 ? '−' : '') + 'A$' + (Math.abs(x) / 10000).toFixed(1) + ' 万';
const pc = (x, d = 1) => x == null ? '30% 以内追不上' : (x * 100).toFixed(d) + '%';
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tipA = t => ` data-tip="${esc(t)}"`;
const ZN = {red: ['✕ 红区', 'crit'], amber: ['! 黄区', 'warn'], green: ['✓ 绿区', 'good']};

function cfg(s, ov) {
  const c = {price: s.price, loan: s.price * s.lvr, rate: s.rate, rev0: s.rev0, peakVal: M.peakVal, offVal: M.offVal, adr: M.adr,
    platformFee: M.platformFee, levy: M.levy || 0, mgmtFee: s.mgmtFee, directCosts: M.directCosts, fixedCosts: s.insurance + s.otherHold, landTax: M.landTax, vrlt: M.vrlt, state: M.state, dutyRate: M.dutyRate, today: CASE.today, optOwn: M.optOwn,
    vrltEscalate: s.vrltEscalate, mtr: s.mtr, years: s.years, cpi: M.cpi, sellPct: M.sellPct, otherCosts: M.otherCosts, furnishing: M.furnishing,
    deposit: s.deposit, index: s.index, homeLoanRate: s.homeLoanRate, bookNights: s.bookNights, bookNightly: s.bookNightly,
    ltRent: s.ltRent, dwelling: M.dwelling, own: {peak: s.peak, off: s.off, peakBlocked: s.peakBlocked, friends: 0}};
  return Object.assign(c, ov || {});
}

// ---------------- SVG helpers
const svg = (w, h, body, label) => `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}">${body}</svg>`;
const txt = (x, y, s, cls, anchor) => `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" class="${cls}"${anchor ? ` text-anchor="${anchor}"` : ''}>${esc(s)}</text>`;
const niceMax = v => { const p = Math.pow(10, Math.floor(Math.log10(Math.max(v, 1)))); const m = v / p; return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p; };

function pathsChart(P, Plo, Phi, Pmid) {
  const keys = ['you', 'opt', 'rent', 'lt', 'dep', 'idx', 'mort'];
  const groups = {you: '度假屋', lt: '长租房', dep: '不买房'};
  const cls = {you: 's2', opt: 's2soft', rent: 's2soft', lt: 's1', dep: 'neu', idx: 'neu', mort: 'neu'};
  const W = 980, L = 250, colW = 300, gap = 70, rh = 44, T = 46;
  const H = T + rh * keys.length + 16;
  const cmax = niceMax(Math.max(...keys.map(k => P.res[k].cashYear)));
  const wabs = niceMax(Math.max(...[P, Plo, Phi, Pmid].flatMap(Q => keys.map(k => Math.abs(Q.res[k].W)))));
  const x1 = v => L + v / cmax * colW;
  const x2z = L + colW + gap + colW / 2, x2 = v => x2z + v / wabs * (colW / 2);
  let g = txt(L, 16, '每年平均要掏多少钱(含度假订房)', 'lab') + txt(L + colW + gap, 16, `${S.years} 年后净身家(房价年涨 ${pc(S.growth)})`, 'lab');
  g += txt(L, 32, '越短越好', 'sub') + txt(L + colW + gap, 32, `越往右越好 · 刻度固定,切换涨幅可直接比长短 · 细线 = 年涨 ${pc(G1)} 到 ${pc(G2)} 的区间`, 'sub');
  [0, cmax / 2, cmax].forEach(v => { g += `<line x1="${x1(v)}" x2="${x1(v)}" y1="${T - 4}" y2="${H - 14}" class="${v ? 'grid' : 'base'}"/>` + txt(x1(v), H - 2, (v / 1000) + 'k', 'ax', 'middle'); });
  [-wabs, -wabs / 2, 0, wabs / 2, wabs].forEach(v => { g += `<line x1="${x2(v)}" x2="${x2(v)}" y1="${T - 4}" y2="${H - 14}" class="${v ? 'grid' : 'base'}"/>` + txt(x2(v), H - 2, (v / 10000) + '万', 'ax', 'middle'); });
  keys.forEach((k, i) => {
    const r = P.res[k], y = T + i * rh;
    if (groups[k] && i) g += `<line x1="0" x2="${W}" y1="${y - 4}" y2="${y - 4}" class="grid"/>`;
    const bold = k === 'you';
    g += txt(0, y + 20, r.label + (r.zone ? '  ' + ZN[r.zone][0] : ''), bold ? 'lab hl' : 'lab');
    g += `<rect x="${L}" y="${y + 6}" width="${Math.max(1.5, x1(r.cashYear) - L).toFixed(1)}" height="22" rx="4" class="${cls[k]}"${tipA(r.label + ':每年平均要掏 ' + fmt(r.cashYear))}/>`;
    g += txt(x1(r.cashYear) + 6, y + 22, fmt(r.cashYear), bold ? 'val hl' : 'val');
    const a = Math.min(x2(0), x2(r.W)), b = Math.max(x2(0), x2(r.W));
    g += `<rect x="${a.toFixed(1)}" y="${y + 6}" width="${Math.max(1.5, b - a).toFixed(1)}" height="22" rx="4" class="${cls[k]}"${tipA(r.label + ':' + S.years + ' 年后净身家 ' + fmt(r.W))}/>`;
    if (k === 'you' || k === 'opt' || k === 'rent' || k === 'lt') { const lo = Plo.res[k].W, hi = Phi.res[k].W;
      g += `<line x1="${x2(lo).toFixed(1)}" x2="${x2(hi).toFixed(1)}" y1="${y + 34}" y2="${y + 34}" class="wh"/><line x1="${x2(lo).toFixed(1)}" x2="${x2(lo).toFixed(1)}" y1="${y + 31}" y2="${y + 37}" class="wh"/><line x1="${x2(hi).toFixed(1)}" x2="${x2(hi).toFixed(1)}" y1="${y + 31}" y2="${y + 37}" class="wh"${tipA(r.label + ':年涨 ' + pc(G1) + ' 时 ' + wan(lo) + ',' + pc(G2) + ' 时 ' + wan(hi))}/>`; }
    g += r.W >= 0 ? txt(b + 6, y + 22, wan(r.W), bold ? 'val hl' : 'val') : txt(a - 6, y + 22, wan(r.W), bold ? 'val hl' : 'val', 'end');
  });
  return svg(W, H + 4, g, '七条路对比');
}

function timeChart(cmpKey, cmpLabel) {
  const T = 20, ys = Array.from({length: T + 1}, (_, i) => i); const C0 = HH.paths(cfg(S), S.growth).C0;
  const series = [['you', '度假屋 · 你的用法', 's2'], ['opt', '度假屋 · 最优排法', 's2soft'], ['lt', '长租房 + 订房', 's1'], ['dep', '存定期 + 订房', 'neu'], ['mort', '还房贷 + 订房', 'neu2']];
  const vals = {_c: []}; series.forEach(([k]) => vals[k] = []);
  ys.forEach(t => { if (t === 0) { series.forEach(([k]) => vals[k].push(C0)); vals._c.push(C0); return; } const r = HH.paths(cfg(S, {years: t}), S.growth).res; series.forEach(([k]) => vals[k].push(r[k].W)); vals._c.push(r[cmpKey].W); });
  const all = series.flatMap(([k]) => vals[k]); const step = niceMax((Math.max(...all) - Math.min(...all)) / 6);
  const lo = Math.floor(Math.min(...all) / step) * step, hi = Math.ceil(Math.max(...all) / step) * step;
  const W = 980, H = 360, L = 70, R = 150, Tp = 20, B = 40;
  const sx = t => L + t / T * (W - L - R), sy = v => Tp + (hi - v) / (hi - lo) * (H - Tp - B);
  let g = '';
  for (let v = lo; v <= hi + 1; v += step) g += `<line x1="${L}" x2="${W - R}" y1="${sy(v).toFixed(1)}" y2="${sy(v).toFixed(1)}" class="${Math.abs(v) < 1 ? 'base' : 'grid'}"/>` + txt(L - 6, sy(v) + 4, Math.round(v / 10000) + ' 万', 'ax', 'end');
  [0, 5, 10, 15, 20].forEach(t => { g += txt(sx(t), H - 18, t ? '第 ' + t + ' 年' : '买入时', 'ax', 'middle'); });
  g += txt((L + W - R) / 2, H - 2, '如果第 N 年卖掉', 'ax', 'middle');
  g += `<line x1="${sx(S.years)}" x2="${sx(S.years)}" y1="${Tp}" y2="${H - B}" class="ref"/>` + txt(sx(S.years) + 4, H - B - 6, '你设定的持有年数', 'ref-t');
  const ends = [];
  series.forEach(([k, nm, c]) => {
    g += `<polyline points="${ys.map((t, i) => sx(t).toFixed(1) + ',' + sy(vals[k][i]).toFixed(1)).join(' ')}" class="ln ${c}-l"/>`;
    ys.forEach((t, i) => { g += `<circle cx="${sx(t).toFixed(1)}" cy="${sy(vals[k][i]).toFixed(1)}" r="3" class="${c} ring"${tipA(nm + ',第 ' + t + ' 年卖掉:净身家 ' + fmt(vals[k][i]))}/>`; });
    ends.push([sy(vals[k][T]), nm]);
  });
  const short = cmpLabel.replace('不买房 · ', '');
  [['you', '你的用法'], ['opt', '最优排法']].forEach(([k, nm], j) => {
    let cross = null;
    for (let i = 1; i <= T; i++) if (vals[k].slice(i).every((v, m) => v >= vals._c[i + m])) { cross = i; break; }
    if (cross != null) { const x = sx(cross), y = sy(vals[k][cross]);
      g += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="8" class="cross"/>` + txt(x - 10, y - 12 - j * 15, `${nm}:第 ${cross} 年追上「${short}」`, 'lab hl', 'end'); }
    else g += txt(L + 8, Tp + 14 + j * 17, `${nm}:20 年内追不上「${short}」`, 'lab hl');
  });
  ends.sort((a, b) => a[0] - b[0]); for (let i = 1; i < ends.length; i++) if (ends[i][0] - ends[i - 1][0] < 17) ends[i][0] = ends[i - 1][0] + 17;
  ends.forEach(([y, nm]) => { g += txt(W - R + 8, y + 4, nm, 'lab'); });
  return svg(W, H, g, '净身家随持有年数变化');
}

function waterfall(h) {
  const m = h.m;
  const steps = [['客人房费', m.rev, 'pos'], ['平台费 15.5%', -m.plat, 'neg'], [`托管 ${Math.round(S.mgmtFee * 100)}%`, -m.mgmt, 'neg'],
    ['清洁、广告', -m.direct, 'neg'], ['持有成本*', -m.hold, 'neg'], ['贷款利息', -m.interest, 'neg'], [m.tax >= 0 ? '所得税' : '退税', -m.tax, m.tax >= 0 ? 'neg' : 'pos'],
    ['每年净结果', m.afterLast, 'tot']];
  let run = 0, lo = 0, hi = 0;
  steps.forEach(([, v, k]) => { if (k === 'tot') { lo = Math.min(lo, v); hi = Math.max(hi, v); } else { run += v; lo = Math.min(lo, run); hi = Math.max(hi, run, run - v); } });
  const W = 760, H = 330, L = 56, R = 12, T = 24, B = 58;
  const span = niceMax((hi - lo) / 4); lo = Math.floor(lo / span) * span; hi = Math.ceil(hi / span) * span + span * 0.3;
  const sy = v => T + (hi - v) / (hi - lo) * (H - T - B), bw = (W - L - R) / steps.length;
  let g = '';
  for (let v = lo; v <= hi; v += span) g += `<line x1="${L}" x2="${W - R}" y1="${sy(v).toFixed(1)}" y2="${sy(v).toFixed(1)}" class="${Math.abs(v) < 1 ? 'base' : 'grid'}"/>` + txt(L - 6, sy(v) + 4, Math.round(v / 1000) + 'k', 'ax', 'end');
  run = 0;
  steps.forEach(([lab, v, k], i) => {
    const x = L + i * bw + bw * 0.18, w = bw * 0.64;
    let a, b; if (k === 'tot') { a = 0; b = v; } else { a = run; b = run + v; run = b; }
    const top = sy(Math.max(a, b)), bot = sy(Math.min(a, b));
    g += `<rect x="${x.toFixed(1)}" y="${top.toFixed(1)}" width="${w.toFixed(1)}" height="${Math.max(bot - top, 1.5).toFixed(1)}" rx="3" class="${{pos: 's1', neg: 's2', tot: 'crit'}[k]}"${tipA(lab + ':' + fmt(v))}/>`;
    if (k !== 'tot' && i < steps.length - 1) g += `<line x1="${x + w}" x2="${x + bw}" y1="${sy(b).toFixed(1)}" y2="${sy(b).toFixed(1)}" class="conn"/>`;
    g += txt(x + w / 2, v >= 0 && k !== 'tot' ? top - 6 : bot + 14, fmt(v), 'val', 'middle') + txt(x + w / 2, H - B + 22, lab, 'ax', 'middle');
  });
  return svg(W, H, g, '一年现金流瀑布图');
}

function scenarioChart() {
  const own = (p, o, b) => ({own: {peak: p, off: o, peakBlocked: b, friends: 0}});
  const rows = [
    ['你设定的用法', `旺季 ${S.peak} 晚 + 淡季 ${S.off} 晚${S.peakBlocked ? ',挡日历' : ''}`, {}],
    ...(M.vrlt ? [['凑满 4 周', `同上,淡季补到合计 28 晚`, own(S.peak, Math.max(S.off, 28 - S.peak), S.peakBlocked)]] : []),
    ['旺季 10 晚不挡', '旺季 10 晚 + 淡季 18 晚', own(10, 18, false)],
    ['最优排法', TX.optShort, own(M.optOwn.peak, M.optOwn.off, false)],
    ['完全不自用', M.vrlt ? '纯出租;度假另订;要交空置税' : '纯出租;度假另订', own(0, 0, false)],
    ['最优排法 + co-host', '同上,托管费 10%', Object.assign(own(M.optOwn.peak, M.optOwn.off, false), {mgmtFee: 0.10})]];
  const data = rows.map(([nm, ds, ov]) => { const h = HH.holidayPath(cfg(S, ov)); return [nm, ds, h.outflows.reduce((a, b) => a + b, 0) / h.outflows.length, h.zone]; });
  data.push(['参照:不买,每年订房', `${S.bookNights} 晚 × A$${S.bookNightly}`, S.bookNights * S.bookNightly, null]);
  const W = 760, L = 230, R = 90, rh = 44, T = 10, H = T + rh * data.length + 30;
  const mx = niceMax(Math.max(...data.map(d => d[2])));
  const sx = v => L + v / mx * (W - L - R);
  let g = '';
  for (let i = 0; i <= 5; i++) { const v = mx * i / 5; g += `<line x1="${sx(v)}" x2="${sx(v)}" y1="${T}" y2="${H - 26}" class="${i ? 'grid' : 'base'}"/>` + txt(sx(v), H - 8, Math.round(v / 1000) + 'k', 'ax', 'middle'); }
  data.forEach(([nm, ds, v, z], i) => {
    const y = T + i * rh, [zl, zc] = z ? ZN[z] : ['', 'ref'];
    g += txt(0, y + 16, nm, 'lab') + txt(0, y + 32, ds, 'sub');
    g += `<rect x="${L}" y="${y + 6}" width="${Math.max(1.5, sx(v) - L).toFixed(1)}" height="24" rx="4" class="${zc}"${tipA(nm + ':每年平均要掏 ' + fmt(v) + (z ? ';ATO ' + zl.slice(2) : ''))}/>`;
    g += txt(sx(v) + 8, y + 23, fmt(v), 'val');
    if (z) g += txt(W - 4, y + 23, zl, 'zl', 'end');
  });
  return svg(W, H, g, '不同自用排法下每年平均要掏的钱');
}

// breakeven growth vs one alternative, on the same yardstick as the headline (null = never within -5%..25%)
function beOne(who, alt, c) {
  c = c || cfg(S); const f = g => { const r = HH.paths(c, g).res; return r[who].W - r[alt].W; };
  let lo = -0.05, hi = 0.25; if (f(lo) >= 0) return lo; if (f(hi) < 0) return null;
  for (let i = 0; i < 30; i++) { const mid = (lo + hi) / 2; if (f(mid) >= 0) hi = mid; else lo = mid; }
  return (lo + hi) / 2;
}
function beAll(who) { const c = cfg(S), o = {}; ['dep', 'idx', 'mort', 'lt'].forEach(k => o[k] = beOne(who, k, c)); return o; }

function breakevenChart(hYou, hOpt) {
  const alts = [['dep', `存定期 ${pc(S.deposit)}`], ['idx', `指数基金 ${pc(S.index)}`], ['mort', `提前还 ${pc(S.homeLoanRate)} 房贷`], ['lt', `买当地长租房`]];
  const bY = beAll('you'), bO = beAll('opt');
  const W = 760, L = 150, R = 40, T = 30, gh = 70, H = T + gh * 4 + 34, mx = 0.12;
  const sx = v => L + Math.min(v, mx) / mx * (W - L - R);
  let g = '';
  for (let v = 0; v <= mx + 1e-9; v += 0.02) g += `<line x1="${sx(v)}" x2="${sx(v)}" y1="${T - 6}" y2="${H - 26}" class="${v ? 'grid' : 'base'}"/>` + txt(sx(v), H - 8, Math.round(v * 100) + '%', 'ax', 'middle');
  CASE.growthRefs.map(r => [r.g, r.label + ' ' + pc(r.g) + '/年']).forEach(([v, l]) => { g += `<line x1="${sx(v)}" x2="${sx(v)}" y1="${T - 6}" y2="${H - 26}" class="ref"/>` + txt(sx(v) + 4, T - 12, l, 'ref-t'); });
  alts.forEach(([k, lab], i) => {
    const y = T + i * gh; g += txt(0, y + 28, lab, 'lab');
    [[bY[k], 's2', '你设定的用法'], [bO[k], 's2soft', '最优排法']].forEach(([v, c, nm], j) => {
      const yy = y + 6 + j * 26;
      if (v == null) { g += txt(L + 4, yy + 15, nm + (k === 'lt' ? ':涨多少都追不上(两套房同涨)' : ':年涨 25% 以内都追不上'), 'val'); return; }
      g += `<rect x="${L}" y="${yy}" width="${Math.max(1.5, sx(Math.max(v, 0)) - L).toFixed(1)}" height="20" rx="3" class="${c}"${tipA(nm + ' vs ' + lab + ':房价每年至少涨 ' + pc(v))}/>` + txt(sx(Math.max(v, 0)) + 6, yy + 15, pc(v), 'val');
    });
  });
  return [svg(W, H, g, '持平涨幅'), bY];
}

function wealthChart() {
  const gs = []; for (let x = -0.01; x <= 0.0901; x += 0.005) gs.push(+x.toFixed(3));
  const series = [['you', '度假屋 · 你的用法', 's2'], ['opt', '度假屋 · 最优排法', 's2soft'], ['lt', '长租房 + 订房', 's1'], ['dep', '存定期 + 订房', 'neu'], ['mort', '还房贷 + 订房', 'neu2']];
  const vals = {}; series.forEach(([k]) => vals[k] = []);
  gs.forEach(g => { const P = HH.paths(cfg(S), g).res; series.forEach(([k]) => vals[k].push(P[k].W)); });
  const all = Object.values(vals).flat(); const lo0 = Math.min(...all), hi0 = Math.max(...all);
  const step = niceMax((hi0 - lo0) / 5); const lo = Math.floor(lo0 / step) * step, hi = Math.ceil(hi0 / step) * step;
  const W = 760, H = 320, L = 64, R = 130, T = 18, B = 40;
  const sx = g => L + (g - gs[0]) / (gs[gs.length - 1] - gs[0]) * (W - L - R), sy = v => T + (hi - v) / (hi - lo) * (H - T - B);
  let g = '';
  for (let v = lo; v <= hi + 1; v += step) g += `<line x1="${L}" x2="${W - R}" y1="${sy(v).toFixed(1)}" y2="${sy(v).toFixed(1)}" class="${Math.abs(v) < 1 ? 'base' : 'grid'}"/>` + txt(L - 6, sy(v) + 4, (v / 10000).toFixed(0) + ' 万', 'ax', 'end');
  [0, 0.02, 0.04, 0.06, 0.08].forEach(v => { g += txt(sx(v), H - 18, (v * 100) + '%', 'ax', 'middle'); });
  g += txt((L + W - R) / 2, H - 2, '假设房价每年涨', 'ax', 'middle');
  [...CASE.growthRefs.map(r => [r.g, r.short]), [S.growth, '当前假设']].forEach(([v, l], i) => { g += `<line x1="${sx(v)}" x2="${sx(v)}" y1="${T}" y2="${H - B}" class="${i == 2 ? 'cur' : 'ref'}"/>` + txt(sx(v) + 4, T + 10 + i * 12, l, 'ref-t'); });
  const ends = [];
  series.forEach(([k, nm, c]) => {
    g += `<polyline points="${gs.map((x, i) => sx(x).toFixed(1) + ',' + sy(vals[k][i]).toFixed(1)).join(' ')}" class="ln ${c}-l"/>`;
    gs.forEach((x, i) => { if (i % 2 === 0) g += `<circle cx="${sx(x).toFixed(1)}" cy="${sy(vals[k][i]).toFixed(1)}" r="3.5" class="${c} ring"${tipA(nm + ',年涨 ' + pc(x) + ':' + S.years + ' 年后净身家 ' + fmt(vals[k][i]))}/>`; });
    ends.push([sy(vals[k][vals[k].length - 1]), nm, c]);
  });
  ends.sort((a, b) => a[0] - b[0]); for (let i = 1; i < ends.length; i++) if (ends[i][0] - ends[i - 1][0] < 17) ends[i][0] = ends[i - 1][0] + 17;
  ends.forEach(([y, nm]) => { g += txt(W - R + 8, y + 4, nm, 'lab'); });
  return svg(W, H, g, '不同房价涨幅下的净身家');
}

// ---------------- controls
const rnd = (v, st) => Math.round(v / st) * st;
const HELP = Object.assign({
  price: '买入价。默认按当地同类房的 typical price。',
  lvr: '贷款占房价的比例。80% = 自己出 20% 首付。',
  rate: '这套房的投资贷款利率,按只还息算。',
  years: '打算持有几年后卖掉。影响首页「N 年后净身家」和持平涨幅。',
  rev0: `假如全年都给客人订、你们一晚不住,一年客人付的房费(不含另收的短住税)。你们每在旺季自住一晚,少收约 A$${M.peakVal};淡季一晚约 A$${M.offVal}。`,
  mgmtFee: `交给托管公司或 co-host 的比例,按扣完 ${Math.round(M.platformFee * 1000) / 10}% 平台费后的房费算。`,
  peak: '你们自己和亲友在暑假、圣诞新年、复活节、长周末住的晚数。ATO 判断时最看重这部分。',
  off: '其他时间住的晚数。冬季、春季学校假期在当地算不算旺季,ATO 认不认,要问注册税务代理。',
  peakBlocked: '「关日历」= 你们打算旺季去住,就提前在 Airbnb 上把那几天关掉,不让客人订,或者客人来问也拒绝。ATO 的例子里,每年都把旺季留给自己,就很可能被认定为「度假屋」:贷款利息、市政费、地税、保险、维修都不能抵税(TR 2026/1 例 12、13)。不勾 = 先让客人订,订剩下的自己再住。',
  insurance: '能覆盖短租的房屋保险。洪水、山火区可能更贵,先拿报价再填。',
  otherHold: '市政费和水费 + 维修和家具更换 + 水电网和日用品,每年合计。',
  vrltEscalate: '维州「空置住宅地税」:一年里没人实际住满 6 个月(客人住的晚数也算),就按房屋总价值交税,第 1 年 1%、连续第 2 年 2%、第 3 年起 3%。你们或亲属一年自己住满 4 周(28 晚),可以申请度假屋豁免。勾上 = 按递增算(SRO 规则);不勾 = 每年都按 1% 算。',
  mtr: '用谁的名字买,就填谁的边际税率。影响每年的税和卖房时的 CGT。',
  deposit: '衡量机会成本用的参照利率:钱不买房,放在定期存款大概能拿的利息(税前)。不指任何具体银行或产品。',
  index: '衡量机会成本用的参照回报:宽基指数基金的长期年回报假设(税前)。不是预测,也不是推荐任何基金。',
  homeLoanRate: '你们自住房的房贷利率。拿这笔钱提前还房贷,省下的利息就是回报,而且省下的是税后的钱。',
  ltRent: '同样的钱在当地买一套长租房,每周能收的租金。',
  bookNights: '你们每年度假一共住几晚。自己的房子住不够这么多晚,差额按订房价计入。',
  bookNightly: '不买房的话,订一间同类房每晚大概多少钱。',
  growth: `房价每年涨多少。只是假设,不是预测。${TX.growthHistory},过去不代表未来。`,
}, CASE.help || {});
const CTL = [
  ['房子与贷款', [['price', '房价', rnd(D0.price * 0.5, 5000), rnd(D0.price * 1.8, 5000), 5000, v => fmt(v)], ['lvr', '贷款比例', 0, 0.8, 0.05, v => pc(v, 0)], ['rate', '投资贷利率', 0.045, 0.09, 0.001, v => pc(v)], ['years', '持有年数', 5, 20, 1, v => v + ' 年']]],
  ['收入与托管', [['rev0', '全年房费(全部给客人时)', rnd(D0.rev0 * 0.4, 500), rnd(D0.rev0 * 2, 500), 500, v => fmt(v), TX.rev0Hint], ['mgmtFee', '托管费', 0, 0.25, 0.01, v => pc(v, 0), '自管 0% · co-host 约 10% · 全托管约 20%']]],
  ['你们怎么住', [['peak', '旺季自用晚数', 0, 42, 1, v => v + ' 晚', '暑假、圣诞新年、复活节、长周末'], ['off', '淡季自用晚数', 0, 60, 1, v => v + ' 晚', '含冬季、春季学校假期(能否算淡季要问税务代理)'], ['peakBlocked', '旺季提前关日历,留给自己住', 'tog']]],
  ['持有成本', [['insurance', '短租保险', 2000, 12000, 250, v => fmt(v), '洪水、山火区可能更贵'], ['otherHold', '市政水费 + 维修 + 水电网', 8000, 25000, 250, v => fmt(v)], ...(M.vrlt ? [['vrltEscalate', '空置税按 1%→2%→3% 逐年递增', 'tog']] : [])]],
  ['税和其他去处', [['mtr', '边际税率', 0.19, 0.45, null, v => pc(v, 0)], ['deposit', '定期利率(税前)', 0.02, 0.065, 0.0025, v => pc(v, 2)], ['index', '指数基金年回报(税前)', 0.03, 0.10, 0.0025, v => pc(v, 2)], ['homeLoanRate', '自住房贷利率', 0.04, 0.09, 0.001, v => pc(v)], ['ltRent', '当地长租周租', rnd(D0.ltRent * 0.6, 5), rnd(D0.ltRent * 1.6, 5), 5, v => fmt(v)]]],
  ['度假', [['bookNights', '每年度假晚数', 7, 42, 1, v => v + ' 晚'], ['bookNightly', '订房每晚价格', 200, 900, 10, v => fmt(v)], ['growth', '假设房价每年涨', -0.02, 0.10, 0.001, v => pc(v), '假设,不是预测;过去不代表未来']]]];

function buildCtls() {
  let h = '';
  CTL.forEach(([gname, items]) => {
    h += `<div class="grp"><h4>${gname}</h4>`;
    items.forEach(([k, lab, a, b, st, f, hint]) => {
      const q = `<span class="q" data-tip="${esc(HELP[k] || '')}" onclick="event.preventDefault();document.getElementById('h_${k}').classList.toggle('on')">?</span>`, hp = `<div class="help" id="h_${k}">${esc(HELP[k] || '')}</div>`;
      if (a === 'tog') h += `<label class="tog"><input type="checkbox" id="c_${k}"> ${lab}${q}</label>${hp}`;
      else if (k === 'mtr') h += `<div class="ctl"><label><span>${lab}${q}</span><output id="o_${k}"></output></label>${hp}<select id="c_${k}" class="btn"><option value="0.19">19%</option><option value="0.325">30%(+Medicare 约 32.5%)</option><option value="0.37">37%</option><option value="0.45">45%</option></select></div>`;
      else h += `<div class="ctl"><label for="c_${k}"><span>${lab}${q}</span><output id="o_${k}"></output></label>${hp}<input type="range" id="c_${k}" min="${a}" max="${b}" step="${st}">${hint ? `<div class="hint">${hint}</div>` : ''}</div>`;
    });
    h += '</div>';
  });
  $('ctls').innerHTML = h;
  $('seg').innerHTML = CASE.growthButtons.map(b => `<button data-g="${b.g}" onclick="setGrowth(${b.g})">${esc(b.label)}</button>`).join(' ');
  CTL.forEach(([, items]) => items.forEach(([k, , a, , , f]) => {
    const el = $('c_' + k);
    el.addEventListener('input', () => { S[k] = a === 'tog' ? el.checked : +el.value; render(); });
  }));
  syncCtls();
}
function syncCtls() {
  CTL.forEach(([, items]) => items.forEach(([k, , a, , , f]) => {
    const el = $('c_' + k); if (a === 'tog') el.checked = !!S[k]; else el.value = S[k];
    if ($('o_' + k)) $('o_' + k).textContent = f(S[k]);
  }));
  document.querySelectorAll('.seg button').forEach(b => b.classList.toggle('on', Math.abs(+b.dataset.g - S.growth) < 1e-6));
}
function setGrowth(g) { S.growth = g; render(); }

// ---------------- render everything
function render() {
  syncCtls();
  const c = cfg(S), P = HH.paths(c, S.growth), you = P.res.you, h = P.hYou;
  const alts = ['dep', 'idx', 'mort', 'lt'].map(k => [k, P.res[k]]).sort((a, b) => b[1].W - a[1].W);
  const best = alts[0][1], bestKey0 = alts[0][0], diff = you.W - best.W, book = S.bookNights * S.bookNightly;
  $('hl').innerHTML = `按你们的用法,这套房每年平均要掏 <span class="big">${fmt(you.cashYear)}</span>,是每年订房(${fmt(book)})的 <span class="big">${(you.cashYear / book).toFixed(1)} 倍</span>;`
    + `房价年涨 ${pc(S.growth)} 的话,${S.years} 年后身家比「${best.label}」${diff < 0 ? '少' : '多'} <span class="big">${wan(Math.abs(diff))}</span>。`;
  const opt = P.res.opt;
  const bestKey = alts[0][0], pv = Math.pow(1.025, S.years);
  const beG = beOne('you', bestKey, c);
  let lo = 0, hi = 250000; for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; const r = HH.paths(cfg(S, {rev0: mid}), S.growth).res; if (r.you.W >= r[bestKey].W) hi = mid; else lo = mid; }
  const revNow = h.m.rev, revNeed = HH.strModel(cfg(S, {rev0: hi}), h.zone).rev;
  const optSave = you.cashYear - opt.cashYear;
  $('flip').innerHTML = `<h3>结论在什么情况下会反过来?(和「${best.label}」比)</h3><ol>`
    + (beG != null ? `<li>房价每年涨超过 <b>${pc(beG)}</b>。${TX.growthHistory},过去不代表未来。</li>`
       : bestKey === 'lt' ? `<li>房价涨多少都没用:长租房和度假屋同涨同跌,差距来自每年的现金流,只能靠下面两条。</li>`
       : `<li>房价每年涨 25% 以上也追不上。</li>`)
    + `<li>你们用法下的全年房费做到 <b>${fmt(revNeed)}</b>,现在按 ${fmt(revNow)} 算,要做到 ${(revNeed / revNow).toFixed(1)} 倍;${TX.revRefs}。</li>`
    + `<li>自用改成最优排法:每年少掏 <b>${fmt(optSave)}</b>,${S.years} 年后差距从 ${wan(diff)} 变成 ${wan(opt.W - best.W)}。</li></ol>`
    + `<p class="small">红旗:${[h.zone === 'red' && S.peakBlocked && '旺季挡日历(ATO 红区)', M.vrlt && S.peak + S.off < 28 && '自住不满 4 周(空置税)', ...TX.redFlags,
        M.dwelling !== 'new_build' && '2027-07-01 起出租亏损不能抵工资'].filter(Boolean).join(' · ')}。</p>`;
  $('hl3').textContent = `${S.years} 年后的金额折成今天的钱(按通胀 2.5%)约为显示数的 ${Math.round(100 / pv)}%;例如上面的差距约合今天的 ${wan(Math.abs(diff) / pv)}。`;
  $('hl2').innerHTML = `就算把自用排到最优(${TX.optDesc}),也要每年掏 ${fmt(opt.cashYear)},${S.years} 年后比「${best.label}」${opt.W - best.W < 0 ? '少' : '多'} ${wan(Math.abs(opt.W - best.W))}。`;
  $('paths').innerHTML = pathsChart(P, HH.paths(c, G1), HH.paths(c, G2), HH.paths(c, D0.growth));
  $('tl').innerHTML = timeChart(bestKey0, best.label);
  const [beSvg, bY] = breakevenChart(h, P.res.opt.h);
  $('kpi2s').textContent = `${TX.growthHistory}(${TX.growthSource})`;
  $('kpi1').textContent = fmt(you.cashYear); $('kpi1s').textContent = `不买、每年订 ${S.bookNights} 晚:${fmt(book)}`;
  $('kpi2').textContent = beG == null ? '追不上' : pc(beG); $('kpi2l').textContent = `房价每年至少要涨(对比「${best.label.replace('不买房 · ', '')}」)`; $('kpi3').textContent = ZN[h.zone][0].slice(2); $('kpi3').className = 'n z-' + h.zone;
  $('kpi3s').textContent = h.zone === 'red' ? '挡旺季日历 ≈ ATO 例 13:利息等持有费不能扣' : h.zone === 'amber' ? '说不准;本页按能分摊扣除算,请找税务代理' : '持有费按出租天数分摊可扣';
  $('kpi4').textContent = fmt(h.upfront); $('kpi4s').textContent = `首付 ${pc(1 - S.lvr, 0)} + 印花税 ${fmt(h.duty)} + 家具和杂费`;
  $('wf').innerHTML = waterfall(h);
  const netOp = h.m.rev - h.m.plat - h.m.mgmt - h.m.direct;
  $('wfTitle').textContent = `房费扣掉平台、托管和清洁剩 ${wan(netOp)},光贷款利息就要 ${wan(h.m.interest)}`;
  $('wfLead').innerHTML = `按你设定的用法,第 ${S.years} 年这一年:${h.zone === 'red' ? 'ATO 红区下利息和持有成本都不能抵税,' : ''}账面 ${fmt(h.m.preTax)},税 ${fmt(-h.m.tax)},每年净结果 <b>${fmt(h.m.afterLast)}</b>。`;
  const own = S.peak + S.off;
  $('wfNote').innerHTML = `* 持有成本 ${fmt(h.m.hold)} = 保险 ${fmt(S.insurance)} + 市政水费、维修、水电网 ${fmt(S.otherHold)} + 土地税 ${fmt(M.landTax)}`
    + (!M.vrlt ? '' : own < 28 ? ` + 空置住宅地税 ${fmt(h.m.hold - S.insurance - S.otherHold - M.landTax)}(自住 ${own} 晚不满 4 周;${S.vrltEscalate ? '按 1%→2%→3% 递增,第 3 年起 3%' : '按每年 1%'})` : '(自住满 4 周,空置税豁免)')
    + `。第一年(2027-07-01 前亏损还能抵工资)净结果 ${fmt(h.m.afterFirst)}。`;
  $('sc').innerHTML = scenarioChart();
  $('be').innerHTML = beSvg;
  $('wl').innerHTML = wealthChart();
  $('dock').innerHTML = `<span>你的用法</span><span class="z pill p-${{red: 'crit', amber: 'warn', green: 'good'}[h.zone]}">${ZN[h.zone][0]}</span>`
    + `<span>每年平均掏 <b>${fmt(you.cashYear)}</b></span><span>持平涨幅 <b>${beG == null ? '追不上' : pc(beG)}</b></span>`
    + `<span class="long">${S.years} 年后比「${best.label}」 <b>${wan(diff)}</b>(年涨 ${pc(S.growth)})</span><a href="#tune">调参数 ↑</a>`;
}
function resetAll() { S = JSON.parse(JSON.stringify(D0)); render(); }

const tipEl = document.getElementById('tip');
document.addEventListener('mousemove', ev => { const el = ev.target.closest('[data-tip]'); if (!el) { tipEl.style.opacity = 0; return; }
  tipEl.textContent = el.getAttribute('data-tip'); tipEl.style.opacity = 1; tipEl.style.left = Math.min(ev.clientX + 14, innerWidth - tipEl.offsetWidth - 8) + 'px'; tipEl.style.top = (ev.clientY + 14) + 'px'; });
if (document.getElementById('cp')) document.getElementById('cp').onclick = () => { navigator.clipboard && navigator.clipboard.writeText(document.getElementById('cp').dataset.t); document.getElementById('cp').textContent = '已复制'; };
buildCtls(); render();
