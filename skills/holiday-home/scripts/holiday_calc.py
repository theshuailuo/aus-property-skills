#!/usr/bin/env python3
"""holiday-home calculator (v0.2): net yield, ATO TR 2026/1 own-use screen,
buy vs book / deposit / index / home loan / long-term rental, keep / long-term / sell.

Standard library only. Usage:
    python holiday_calc.py input.json                    # print JSON results
    python holiday_calc.py input.json --html report.html # also render the report

All money is AUD; flows are per year, in today's dollars (no rent inflation).
Every default is echoed under "assumptions" so the report can show it.
Simplifications are listed in SIMPLIFICATIONS and printed in the result.
"""
import argparse
import html
import json
import sys
from datetime import date
from html.parser import HTMLParser

DEFAULTS = {
    "mode": "buy",                 # buy | own
    "lang": "zh",                  # zh | en
    "state": None,                 # NSW | VIC | QLD -> stamp duty computed; others need stamp_duty
    "years": 10,
    "price": 0,                    # buy: purchase price; own: current market value
    "dwelling": "established",     # established | new_build (2026 negative gearing reform)
    "acquired_before_2026_05_12": False,   # own: held before 7:30pm AEST 12 May 2026
    "stamp_duty": None,            # None -> state table (NSW/VIC/QLD) or 4% rough estimate, flagged
    "other_purchase_costs": 3000,  # legal, inspections
    "furnishing": 30000,
    "loan": 0,
    "interest_rate": 0.06,         # interest-only assumed
    # revenue: either gross_rent, or nightly_rate + occupancy (then caps and own use are applied)
    "gross_rent": 0,               # guest-paid revenue per year, own-use nights already removed
    "nightly_rate": 0,
    "occupancy": 0,                # share of nights available to guests that get booked
    "cap_nights": None,            # e.g. 180 (NSW Greater Sydney), 60 (Byron), 90 (Perth without DA)
    "revenue_range": None,         # [low, high] gross_rent; adds sensitivity rows
    "platform_fee": 0.155,         # Airbnb host-only fee; 0.03 for split fee
    "short_stay_levy": 0.0,        # VIC 0.075; ACT 0.05 (0.075 from 2027-07-01); stays < 28 nights
    "mgmt_fee": 0.20,              # on revenue net of platform fee; ~0.10 co-host; 0 self-managed
    "fixed_costs": {               # ownership / use costs: denied if TR 2026/1 test fails (add "strata" etc.)
        "insurance": 5000, "council_water": 3500, "repairs_maintenance": 10000,
        "utilities_internet": 5000,
    },
    "direct_costs": {              # only for letting: still deductible
        "cleaning_net": 3000, "advertising_other": 500,
    },
    "land_tax": 0,
    "marginal_tax_rate": 0.37,
    "own_use": {
        "peak_nights": 0,          # school holidays, Christmas-New Year, Easter, long weekends
        "offpeak_nights": 0,
        "peak_blocked": False,     # owner blocks peak periods from guests
        "friends_discount_nights": 0,
        "commercial_pricing": True,
        "refuses_bookings": False,  # refuses enquiries or cancels bookings to keep dates for itself
    },
    "effort": {"hours_per_year": 0, "hourly_value": 0},
    "growth": None,
    "growth_scenarios": [],        # sensitivity points only; the headline is the breakeven
    "selling_cost_pct": 0.025,
    "booking": {"weeks_per_year": 4, "nightly": 400},
    "alt_returns": {"deposit": 0.045, "index": 0.07},
    "home_loan_rate": None,        # set -> compare with paying down a non-deductible home loan
    "cpi": 0.025,
    "lt_property": {               # buy: same money into a long-term rental, holidays booked
        "price": None, "weekly_rent": 0, "vacancy_weeks": 2, "mgmt_fee": 0.07,
        "fixed_costs": None, "land_tax": 0, "dwelling": "established",
        "growth_refs": [0.03, 0.05],
    },
    # own mode
    "cost_base": 0,
    "value_at_2027_07_01": None,
    "long_term": {"weekly_rent": 0, "vacancy_weeks": 2, "mgmt_fee": 0.07, "fixed_costs": 16000},
    "what_if": [],                 # [{"label": "...", <overrides>}, ...]
    "video_url": "https://www.youtube.com/@shuailuo",   # replace with this skill's video once published
}

SIMPLIFICATIONS_ZH = [
    "租金和费用按今天的钱、不涨价",
    "只还息贷款,卖房时一次还清",
    "被隔离的亏损先抵以后的租金利润,再抵卖房的资本利得",
    "指数基金回报按边际税率的一半粗算税",
    "没算折旧和资本工程扣除",
    "CGT 简化:2027-07-01 前的涨幅 50% 折扣,之后按通胀指数化、最低 30% 税率",
]

SIMPLIFICATIONS = [
    "rents and costs held flat in today's dollars",
    "interest-only loan, balance repaid at sale",
    "quarantined losses offset later rental profit, then the capital gain at sale",
    "index fund return taxed at half the marginal rate as a rough drag",
    "depreciation and capital works deductions not modelled",
    "CGT simplified: 50% discount on gains to 2027-07-01, indexation and 30% minimum after",
]

REFORM = date(2027, 7, 1)

# Stamp duty (general rates, not first-home or foreign surcharge). Verified 2026-10-23.
# NSW 2026/27 (CPI-indexed each 1 July): revenue.nsw.gov.au/taxes-duties-levies-royalties/transfer-duty/rates
# VIC non-principal place of residence: sro.vic.gov.au (updated 29 Sep 2026)
# QLD general rates: qro.qld.gov.au/duties/transfer-duty/calculate/rates/ (updated 25 Jun 2026)
DUTY = {
    "NSW": [(0, 0, 0.0125), (18000, 225, 0.015), (38000, 525, 0.0175), (103000, 1662, 0.035),
            (387000, 11602, 0.045), (1290000, 52237, 0.055)],
    "QLD": [(5000, 0, 0.015), (75000, 1050, 0.035), (540000, 17325, 0.045), (1000000, 38025, 0.0575)],
}


def stamp_duty(state, v):
    if state == "VIC":
        if v <= 25000:
            return v * 0.014
        if v <= 130000:
            return 350 + (v - 25000) * 0.024
        if v <= 960000:
            return 2870 + (v - 130000) * 0.06
        if v <= 2000000:
            return v * 0.055
        return 110000 + (v - 2000000) * 0.065
    table = DUTY.get(state)
    if not table:
        return None
    if state == "QLD" and v <= 5000:
        return 0.0
    base_from, base, rate = table[0]
    for frm, b, r in table:
        if v > frm:
            base_from, base, rate = frm, b, r
    return base + (v - base_from) * rate


def merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            out[k] = merge(base[k], v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------- ATO screen
def ato_screen(u):
    """Rough compliance-risk screen after PCG 2026/3 zones and TR 2026/1 examples. Not a ruling;
    the ATO examples are illustrative only (PCG para 21).
    red   ~ PCG para 56 factors: peak times blocked out for personal use each year, refusing or
            cancelling bookings, non-commercial terms; TR ex 12-13; PCG ex 8-11
    amber ~ PCG ex 5-7 (ex 5: a few months of peak use each year is still amber); the 8-night
            line is this skill's own
    green ~ PCG ex 1-4"""
    peak, off, friends = u["peak_nights"], u["offpeak_nights"], u["friends_discount_nights"]
    red = []
    if u["peak_blocked"]:
        red.append("peak_blocked_each_year")
    if u.get("refuses_bookings"):
        red.append("refuses_or_cancels_bookings")
    if not u["commercial_pricing"]:
        red.append("non_commercial_terms")
    if red:
        return "likely_fail", red
    amber = []
    if peak > 7:
        amber.append("peak_self_use_over_1_week")
    if off > 28:
        amber.append("offpeak_self_use_over_4_weeks")
    if friends > 0:
        amber.append("friends_low_or_no_cost")
    return ("uncertain", amber) if amber else ("likely_pass", [])


# ---------------------------------------------------------------- years
def years_before_reform():
    return max(0.0, (REFORM - date.today()).days / 365.25)


def quarantined_in_year(c, t):
    """t is 1-based. Year t starts (t-1) years from today."""
    if c["dwelling"] == "new_build":
        return False
    if c["mode"] == "own" and c["acquired_before_2026_05_12"]:
        return False
    return (t - 1) >= years_before_reform()


def revenue(c):
    if c["gross_rent"]:
        return c["gross_rent"], None
    u = c["own_use"]
    private = u["peak_nights"] + u["offpeak_nights"] + u["friends_discount_nights"]
    nights = (365 - private) * c["occupancy"]
    capped = False
    if c["cap_nights"] is not None and nights > c["cap_nights"]:
        nights, capped = c["cap_nights"], True
    return nights * c["nightly_rate"], {"guest_nights": nights, "capped": capped}


def tax_series(c, taxable_each_year, flag_fn):
    """Apply the 2026 loss quarantine year by year. Returns (taxes, remaining_pool)."""
    pool, taxes = 0.0, []
    mtr = c["marginal_tax_rate"]
    for t, ti in enumerate(taxable_each_year, 1):
        if ti < 0 and flag_fn(t):
            pool += -ti
            taxes.append(0.0)
        elif ti > 0 and pool > 0:
            used = min(pool, ti)
            pool -= used
            taxes.append((ti - used) * mtr)
        else:
            taxes.append(ti * mtr)
    return taxes, pool


def str_model(c, screen):
    rev, rev_detail = revenue(c)
    levy = rev * c["short_stay_levy"]
    plat = rev * c["platform_fee"]
    mgmt = (rev - plat) * c["mgmt_fee"]
    direct = sum(c["direct_costs"].values())
    hold = sum(c["fixed_costs"].values()) + c["land_tax"]
    interest = c["loan"] * c["interest_rate"]
    effort = c["effort"]["hours_per_year"] * c["effort"]["hourly_value"]
    noi = rev - levy - plat - mgmt - direct - hold
    pre_tax = noi - interest
    u = c["own_use"]
    private = u["peak_nights"] + u["offpeak_nights"] + u["friends_discount_nights"]
    share = 0.0 if screen == "likely_fail" else max(0.0, (365 - private) / 365)
    deductions = levy + plat + mgmt + direct + (hold + interest) * share
    denied = (hold + interest) * (1 - share)
    taxable = rev - deductions
    n = c["years"]
    taxes, pool = tax_series(c, [taxable] * n, lambda t: quarantined_in_year(c, t))
    after = [pre_tax - tx - effort for tx in taxes]
    year = {
        "revenue": rev, "revenue_detail": rev_detail, "short_stay_levy": levy, "platform_fee": plat,
        "management": mgmt, "direct_costs": direct, "holding_costs": hold, "interest": interest,
        "effort_cost": effort, "noi": noi, "pre_tax_cash": pre_tax,
        "deductible_holding_share": share, "denied_holding_costs": denied,
        "taxable_income": taxable,
        # representative year = the last one (steady state after the reform)
        "tax": taxes[-1], "after_tax_cash": after[-1],
        "first_year_after_tax_cash": after[0],
        "loss_quarantined": any(quarantined_in_year(c, t) for t in range(1, n + 1)) and taxable < 0,
    }
    return year, after, pool


def lt_model(c, cfg_lt):
    rev = cfg_lt["weekly_rent"] * (52 - cfg_lt["vacancy_weeks"])
    mgmt = rev * cfg_lt["mgmt_fee"]
    hold = cfg_lt["fixed_costs"] + c["land_tax"]
    interest = c["loan"] * c["interest_rate"]
    pre_tax = rev - mgmt - hold - interest
    n = c["years"]
    taxes, pool = tax_series(c, [pre_tax] * n, lambda t: quarantined_in_year(c, t))
    after = [pre_tax - tx for tx in taxes]
    return {"revenue": rev, "management": mgmt, "holding_costs": hold, "interest": interest,
            "pre_tax_cash": pre_tax, "tax": taxes[-1], "after_tax_cash": after[-1]}, after, pool


# ---------------------------------------------------------------- CGT and wealth
def cgt(c, sale_value, cost_base, n, growth):
    """Simplified. Gains to 2027-07-01 keep the 50% discount; later gains indexed, min 30% rate."""
    mtr = c["marginal_tax_rate"]
    pre = years_before_reform()
    if n <= pre:
        return max(0.0, sale_value - cost_base) * 0.5 * mtr
    v1 = c["value_at_2027_07_01"]
    if v1 is None:
        v1 = c["price"] * (1 + growth) ** pre
    if c["mode"] == "buy":
        v1 = max(v1, cost_base) if pre > 0 else cost_base
    pre_tax = max(0.0, v1 - cost_base) * 0.5 * mtr
    indexed = max(v1, cost_base) * (1 + c["cpi"]) ** (n - pre)
    post_tax = max(0.0, sale_value - indexed) * max(mtr, 0.30)
    return pre_tax + post_tax


def exit_value(c, g, cost_base, denied_total, pool):
    """Net cash from selling at year n: price after growth, less selling costs, loan and CGT."""
    n = c["years"]
    sale = c["price"] * (1 + g) ** n
    sell_cost = sale * c["selling_cost_pct"]
    tax = cgt(c, sale, cost_base + denied_total + sell_cost, n, g)
    tax = max(0.0, tax - pool * c["marginal_tax_rate"])
    return sale - sell_cost - c["loan"] - tax


def fv(cash_by_year, r):
    n = len(cash_by_year)
    return sum(x * (1 + r) ** (n - t) for t, x in enumerate(cash_by_year, 1))


def solve(fn, lo=-0.10, hi=0.30):
    """Smallest growth rate g where fn(g) >= 0 (fn increasing). None if not reached."""
    if fn(lo) >= 0:
        return lo
    if fn(hi) < 0:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if fn(mid) >= 0 else (mid, hi)
    return (lo + hi) / 2


def alt_rates(c):
    """After-tax return on the lump sum for each alternative. Money added or saved each year is
    counted at the after-tax deposit rate in every path (one yardstick), so paths rank the same way
    in the script and in the interactive report."""
    mtr = c["marginal_tax_rate"]
    out = {"deposit": c["alt_returns"]["deposit"] * (1 - mtr),
           "index": c["alt_returns"]["index"] * (1 - mtr * 0.5)}
    if c.get("home_loan_rate"):
        out["mortgage"] = c["home_loan_rate"]   # interest saved, paid from after-tax income
    return out


def booking_cost(c):
    b = c["booking"]
    return b["weeks_per_year"] * 7 * b["nightly"]


def duty_for(c, price):
    if c["stamp_duty"] is not None and price == c["price"]:
        return c["stamp_duty"], "input"
    d = stamp_duty(c["state"], price)
    if d is not None:
        return d, "state_table"
    return price * 0.04, "rough_4pct"


def growth_points(c):
    return ([c["growth"]] if c["growth"] is not None else []) + list(c["growth_scenarios"])


# ---------------------------------------------------------------- buy
def compare_buy(c, year, after, pool):
    stamp, stamp_src = duty_for(c, c["price"])
    upfront = c["price"] - c["loan"] + stamp + c["other_purchase_costs"] + c["furnishing"]
    cost_base = c["price"] + stamp + c["other_purchase_costs"]
    denied_total = year["denied_holding_costs"] * c["years"]
    book = booking_cost(c)
    n = c["years"]
    rd = alt_rates(c)["deposit"]
    out = {"upfront_cash": upfront, "stamp_duty_used": stamp, "stamp_duty_source": stamp_src,
           "booking_cost_per_year": book, "by_alternative": {}}
    for name, r in alt_rates(c).items():
        other = upfront * (1 + r) ** n + fv([-a - book for a in after], rd)

        def gap(g):
            return exit_value(c, g, cost_base, denied_total, pool) - other
        out["by_alternative"][name] = {
            "after_tax_return": r, "other_wealth": other, "breakeven_growth": solve(gap),
            "scenarios": {f"{g:.3f}": gap(g) for g in growth_points(c)}}
    lp = c["lt_property"]
    if lp["weekly_rent"]:
        out["vs_long_term_property"] = compare_lt_property(c, after, pool, stamp / c["price"],
                                                           cost_base, denied_total, upfront)
    return out


def compare_lt_property(c, after_h, pool_h, duty_rate, cb_h, denied_h, up_h):
    lp, n = c["lt_property"], c["years"]
    lt_price = lp["price"] or c["price"]
    lvr = c["loan"] / c["price"] if c["price"] else 0
    cc = merge(c, {"price": lt_price, "loan": lt_price * lvr, "land_tax": lp["land_tax"],
                   "dwelling": lp["dwelling"], "value_at_2027_07_01": None})
    lt_cfg = {"weekly_rent": lp["weekly_rent"], "vacancy_weeks": lp["vacancy_weeks"],
              "mgmt_fee": lp["mgmt_fee"],
              "fixed_costs": lp["fixed_costs"] if lp["fixed_costs"] is not None else lt_price * 0.012}
    lt_year, lt_after, lt_pool = lt_model(cc, lt_cfg)
    lt_duty = stamp_duty(c["state"], lt_price) if c["state"] else None
    lt_duty = lt_duty if lt_duty is not None else lt_price * duty_rate
    up_lt = lt_price - cc["loan"] + lt_duty + c["other_purchase_costs"]
    cb_lt = lt_price + lt_duty + c["other_purchase_costs"]
    book = booking_cost(c)
    r = alt_rates(c)["deposit"]
    diff = [a - (b - book) for a, b in zip(after_h, lt_after)]

    def wealth_h(g):
        return exit_value(c, g, cb_h, denied_h, pool_h) + fv(diff, r)

    def wealth_lt(g):
        return exit_value(cc, g, cb_lt, 0.0, lt_pool) + (up_h - up_lt) * (1 + r) ** n

    refs = {}
    for g_lt in lp["growth_refs"]:
        target = wealth_lt(g_lt)
        need = solve(lambda g: wealth_h(g) - target)
        refs[f"{g_lt:.3f}"] = {"holiday_growth_needed": need,
                               "premium": None if need is None else need - g_lt}
    return {"lt_price": lt_price, "lt_year": lt_year, "booking_cost_per_year": book,
            "annual_cash_holiday_minus_lt": diff[-1], "growth_refs": refs}


# ---------------------------------------------------------------- own
def compare_own(c, year, after, pool):
    n = c["years"]
    book = booking_cost(c)
    lt_year, lt_after, lt_pool = lt_model(c, c["long_term"])
    sell_cost = c["price"] * c["selling_cost_pct"]
    now_tax = cgt(c, c["price"], c["cost_base"] + sell_cost, 0, 0.0)
    sell_now = c["price"] - sell_cost - c["loan"] - now_tax
    out = {"booking_cost_per_year": book, "long_term_year": lt_year,
           "sell_now": {"net_proceeds": sell_now, "cgt_estimate": now_tax}, "by_alternative": {}}
    denied_total = year["denied_holding_costs"] * n
    rd = alt_rates(c)["deposit"]
    for name, r in alt_rates(c).items():
        sell_w = sell_now * (1 + r) ** n + fv([-book] * n, rd)

        def keep(g):
            return exit_value(c, g, c["cost_base"], denied_total, pool) + fv(after, rd)

        def lt(g):
            return exit_value(c, g, c["cost_base"], 0.0, lt_pool) + fv([x - book for x in lt_after], rd)

        out["by_alternative"][name] = {
            "after_tax_return": r,
            "breakeven_growth_keep_vs_sell": solve(lambda g: keep(g) - sell_w),
            "breakeven_growth_long_term_vs_sell": solve(lambda g: lt(g) - sell_w),
            "scenarios": {f"{g:.3f}": {"keep_str": keep(g), "long_term": lt(g), "sell_now": sell_w}
                          for g in growth_points(c)}}
    return out


# ---------------------------------------------------------------- run
def core(c):
    screen, reasons = ato_screen(c["own_use"])
    year, after, pool = str_model(c, screen)
    res = {"ato_screen": {"result": screen, "reasons": reasons}, "str_year": year,
           "str_year_if_fail": str_model(c, "likely_fail")[0] if screen == "uncertain" else None,
           "yields": {"gross": year["revenue"] / c["price"] if c["price"] else None,
                      "net_before_interest": year["noi"] / c["price"] if c["price"] else None}}
    res["comparison"] = (compare_buy if c["mode"] == "buy" else compare_own)(c, year, after, pool)
    return res


def headline(c, res):
    alt = res["comparison"]["by_alternative"]["deposit"]
    key = "breakeven_growth" if c["mode"] == "buy" else "breakeven_growth_keep_vs_sell"
    return {"ato": res["ato_screen"]["result"], "after_tax_cash": res["str_year"]["after_tax_cash"],
            "breakeven_vs_deposit": alt[key]}


def run(inp):
    c = merge(DEFAULTS, inp)
    res = core(c)
    res["assumptions"] = c
    res["simplifications"] = SIMPLIFICATIONS
    rows = []
    if c["revenue_range"]:
        for label, v in zip(("revenue_low", "revenue_high"), c["revenue_range"]):
            cc = merge(c, {"gross_rent": v})
            rows.append({"label": label, "gross_rent": v, **headline(cc, core(cc))})
    for w in c["what_if"]:
        w = dict(w)
        label = w.pop("label", "what_if")
        cc = merge(c, w)
        rows.append({"label": label, **headline(cc, core(cc))})
    res["what_if"] = rows
    return res


# ---------------------------------------------------------------- HTML report
L = {
    "zh": {
        "title": "度假屋测算", "buy": "想买:买还是订", "own": "已有:留着、改长租还是卖掉",
        "ato": "ATO TR 2026/1 自用测试(粗筛)",
        "likely_pass": "绿区:大概率算「主要用于出租」,持有成本按出租天数分摊可扣",
        "likely_fail": "红区(PCG 2026/3 合规风险分级):ATO 很可能认为它不是主要用于出租,而是度假屋。如果这样认定:租金照样交税;利息、市政费、地税、维修(以及按 TR para 35 推断的保险、strata、水费)不能扣。被否的是扣除本身,不形成可结转的亏损,唯一去向是卖房时计入 CGT 成本基数(para 95);平台费、清洁、广告这类直接费用照扣",
        "uncertain": "黄区:说不准。下面另算了被判度假屋时的账;建议拿真实日历找注册税务代理看",
        "if_fail": "如果被判成度假屋:税后现金流",
        "red_tax": "为什么现金流是负的还要交税:红区下利息和持有成本不能扣,只有直接费用能扣,所以租金扣完直接费用后仍是应税收入。",
        "net": "一年的账(稳定年份)", "rev": "客人支付总额", "levy": "短住税(VIC / ACT)",
        "plat": "平台费", "mgmt": "托管", "direct": "清洁、广告等直接费用",
        "hold": "保险、市政费、维修、水电、地税", "interest": "贷款利息", "pre": "税前现金流",
        "tax": "税(负数=要交,正数=退税)", "effort": "自己花的时间(折现)", "after": "税后现金流",
        "first": "第一年(2027-07-01 前亏损还能抵工资)税后现金流",
        "gross": "毛收益率", "netY": "净收益率(未扣利息)", "cmp": "对比",
        "upfront": "买房前期现金(首付 + 印花税 + 杂费 + 家具)", "duty": "印花税",
        "duty_src": {"input": "你给的", "state_table": "按州政府现行税率表算", "rough_4pct": "按房价 4% 粗估,请用州税务局计算器替换"},
        "alt_disc": "先读这句:本节是一般信息,只是把买度假屋要拿出的钱,和存定期、买指数基金、提前还房贷这几种常见去处放在一起比机会成本。这里用的是通用假设的参照回报率,不指任何具体产品、银行或基金;没有结合您的个人情况,不构成金融产品建议,也不是对任何产品的推荐。您的税率、贷款、风险承受力和时间安排都会改变结论,请结合自身情况自行分析,或寻求持牌专业人士意见。",
        "net_def": "口径:净收益率 = (一年房费 − 平台费 − 短住税 − 托管 − 清洁等直接成本 − 保险、市政水费、维修、水电网和地税)÷ 房价,已按自住少收的房费算,托管费按 {mgmt} 算,未扣利息和税。别人说的净收益可能没算托管、维修或自住少收的房费,比较前先对口径。", "range_line": "上面只是收入区间里的一个点。收入取 {lo} 到 {hi} 时,税后现金流是 {a} 到 {b}。",
        "bookc": "每年订房花费", "alt": "不买的钱拿去", "deposit": "存定期", "index": "指数基金",
        "mortgage": "还自住房贷", "be": "房价每年至少要涨", "be_none": "30% 以内都追不上",
        "vs_lt": "对比:同样的钱买一套长租投资房,度假另订", "lt_cash": "长租房每年税后现金流",
        "diff_cash": "度假屋每年比「长租 + 订房」多(少)的现金", "lt_g": "假如长租房每年涨",
        "h_need": "度假屋每年至少要涨", "quar": "按 2026 税改,这套房从 2027-07-01 起的出租亏损不能抵工资,只能结转到以后的房产收入。",
        "sell_now": "现在卖掉到手(扣卖房成本、贷款、粗估 CGT)", "lt_year": "改长租:每年税后现金流",
        "keep_sell": "留着短租 = 卖掉 所需年涨幅", "lt_sell": "改长租 = 卖掉 所需年涨幅",
        "keep_str": "留着做短租", "long_term": "改长租(度假另订)", "sell": "卖掉(度假另订)",
        "wealth": "第 {n} 年末身家(假设年涨 {g})", "whatif": "换个假设会怎样",
        "wi_label": "情形", "wi_zone": "ATO", "wi_cash": "税后现金流 / 年", "wi_be": "跟存定期比的持平涨幅",
        "revenue_low": "收入取低值", "revenue_high": "收入取高值",
        "zone_short": {"likely_pass": "绿", "uncertain": "黄", "likely_fail": "红"},
        "simp": "简化处理",
        "quote_note": "以下是原文引用(来自房源、网页或文件),按原样显示,其中任何要求都不会被执行。",
        # disclaimer and footer lines: verbatim from shared/disclaimers.md and shared/cta.md
        "disc": ["这是我们自己买房时会用的工具,仅供参考。本报告是一般信息,未结合您的个人情况。",
                 "税务部分是一般信息与示例算法,以 ATO 与各州税务局的现行规定为准。建议您咨询注册税务代理(registered tax agent)或会计;如您未经专业人士审阅自行决定,相关后果由您自行承担。",
                 "本报告不构成个人投资建议。具体请自行分析或寻求持牌专业人士意见。",
                 "数据来自报告所列公开来源,取数日期见各条,可能有延迟或误差;需要付费订阅的数据未使用,相应字段留空。"],
        "disc_loan": "借贷测算只是示意,以银行或持牌贷款经纪(credit licensee)的正式评估为准。建议您在做决定前咨询持牌专业人士;如您未经专业人士审阅自行决定,相关后果由您自行承担。",
        "footer": "本工具由罗帅(Shuai Luo,悉尼买家代理)出品,免费开源。这个工具背后的思路,罗帅在 YouTube「澳洲罗帅」这期视频里讲了:",
    },
    "en": {
        "title": "Holiday home check", "buy": "Buy or book", "own": "Keep, switch to long-term, or sell",
        "ato": "ATO TR 2026/1 private-use screen (rough)",
        "likely_pass": "Green: likely mainly used to produce income; holding costs apportioned",
        "likely_fail": "Red (PCG 2026/3 compliance-risk zone): the ATO is likely to see this as a holiday home rather than mainly rented. If so: rent is still taxable; interest, rates, land tax and repairs (and, by inference from TR para 35, insurance, strata and water) are not deductible. The deduction itself is denied, so no loss carries forward; the only place these costs go is the CGT cost base (para 95). Platform fees, cleaning and advertising stay deductible",
        "uncertain": "Amber: unclear. The holiday-home case is shown below; take your real calendar to a registered tax agent",
        "if_fail": "If treated as a holiday home: after-tax cash flow",
        "red_tax": "Why tax is payable while cash flow is negative: in the red zone interest and holding costs are not deductible, only direct costs are, so rent less direct costs is still taxable.",
        "net": "One year of numbers (steady year)", "rev": "Guest-paid revenue", "levy": "Short stay levy (VIC / ACT)",
        "plat": "Platform fee", "mgmt": "Management", "direct": "Cleaning, advertising (direct costs)",
        "hold": "Insurance, rates, repairs, utilities, land tax", "interest": "Loan interest",
        "pre": "Pre-tax cash flow", "tax": "Tax (negative = payable, positive = refund)",
        "effort": "Your own time (valued)", "after": "After-tax cash flow",
        "first": "First year (losses still offset salary before 1 July 2027) after-tax cash flow",
        "gross": "Gross yield", "netY": "Net yield (before interest)", "cmp": "Comparison",
        "upfront": "Upfront cash (deposit + stamp duty + costs + furniture)", "duty": "Stamp duty",
        "duty_src": {"input": "your figure", "state_table": "from the state's current rate table", "rough_4pct": "rough 4% of price; replace with the state calculator"},
        "alt_disc": "Read this first: This section is general information. It sets the money a holiday home ties up against a few common alternatives (a term deposit, an index fund, paying down your home loan) to show the opportunity cost. The rates are generic reference assumptions, not any specific product, bank or fund. It does not take your personal circumstances into account, is not financial product advice and does not recommend any product. Your tax rate, loans, risk tolerance and timing all change the result; please weigh it against your own situation, or seek advice from a licensed professional.",
        "net_def": "Basis: net yield = (a year's room revenue − platform fee − short-stay levy − management − cleaning and other direct costs − insurance, rates, water, repairs, utilities and land tax) ÷ price, after the revenue lost to your own stays, with management at {mgmt}, before interest and tax. Figures quoted by others may leave out management, repairs or the revenue lost to own stays, so check the basis before comparing.", "range_line": "That is one point in the revenue range. With revenue from {lo} to {hi}, after-tax cash flow runs from {a} to {b}.",
        "bookc": "Booking holidays instead, per year", "alt": "Money not used to buy goes to",
        "deposit": "Term deposit", "index": "Index fund", "mortgage": "Pay down home loan",
        "be": "Prices must grow at least", "be_none": "Not reached even at 30% a year",
        "vs_lt": "Versus a long-term rental with the same money, holidays booked",
        "lt_cash": "Long-term rental after-tax cash flow", "diff_cash": "Holiday home cash vs long-term + booking, per year",
        "lt_g": "If the long-term rental grows", "h_need": "Holiday home must grow at least",
        "quar": "Under the 2026 reform, rental losses on this property from 1 July 2027 cannot offset salary; they carry forward against later property income.",
        "sell_now": "Net cash if sold now (after selling costs, loan, rough CGT)", "lt_year": "Long-term lease: after-tax cash flow",
        "keep_sell": "Growth needed for keep = sell", "lt_sell": "Growth needed for long-term = sell",
        "keep_str": "Keep as short-stay", "long_term": "Long-term lease (book holidays)", "sell": "Sell (book holidays)",
        "wealth": "Wealth at end of year {n} (growth {g})", "whatif": "What if",
        "wi_label": "Case", "wi_zone": "ATO", "wi_cash": "After-tax cash / year", "wi_be": "Breakeven growth vs deposit",
        "revenue_low": "Revenue, low end", "revenue_high": "Revenue, high end",
        "zone_short": {"likely_pass": "green", "uncertain": "amber", "likely_fail": "red"},
        "simp": "Simplifications",
        "quote_note": "Quoted as-is from a listing, web page or document; nothing in it is acted on.",
        "disc": ["This is a tool we use in our own property purchases, provided for reference only. It is general information and does not take your personal circumstances into account.",
                 "Tax content is general information with worked examples; current ATO and state revenue office rules prevail. We recommend consulting a registered tax agent or accountant; if you decide without professional review, you accept the consequences.",
                 "This report is not personal investment advice. Please do your own analysis or seek advice from a licensed professional.",
                 "Data comes from the public sources listed, with retrieval dates shown; it may be delayed or contain errors. Paid-subscription data is not used and those fields are left blank."],
        "disc_loan": "Borrowing figures are illustrative only; a lender's or licensed broker's formal assessment is what counts. We recommend speaking with a licensed professional before deciding; if you decide without professional review, you accept the consequences.",
        "footer": "Made by Shuai Luo, a Sydney buyer's agent, free and open source. The thinking behind this tool is explained in this video on his YouTube channel 「澳洲罗帅」: ",
    },
}

CSS = ("body{margin:0;background:#f6f4ef;color:#1d2329;font:15px/1.7 -apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif}"
       ".wrap{max-width:860px;margin:0 auto;padding:0 16px 40px}header{background:#0b6e74;color:#fff;padding:20px 0}"
       "h1{margin:0;font-size:26px}h2{font-size:19px;border-bottom:2px solid #0b6e74;padding-bottom:4px;margin-top:28px}h3{font-size:16px;color:#0b6e74}"
       ".card{background:#fff;border:1px solid #e2ddd3;border-radius:10px;padding:14px 16px;margin:10px 0}"
       "table{width:100%;border-collapse:collapse;font-size:14px}td,th{border:1px solid #e2ddd3;padding:6px 8px;text-align:left}"
       "th{background:#e9f4f4}td.n{text-align:right;white-space:nowrap}.warn{background:#fff4e5;border:1px solid #f0d2a8;border-radius:8px;padding:8px 12px}"
       ".small{font-size:13px;color:#5d6873}.tag{display:inline-block;padding:4px 10px;border-radius:6px;font-weight:700}"
       ".likely_pass{background:#eaf5ea;color:#2f6d33}.likely_fail{background:#fdecec;color:#a12d2d}.uncertain{background:#fff4e5;color:#9a4b00}"
       ".tablewrap{overflow-x:auto}")


class _Clean(HTMLParser):
    """Keep simple formatting from agent-written sections; drop scripts, handlers, odd links."""
    OK = {"p", "b", "strong", "i", "em", "ul", "ol", "li", "br", "a", "table", "tr", "td", "th",
          "thead", "tbody", "h3", "h4", "span", "div", "small", "code", "blockquote"}
    DROP = {"script", "style", "iframe", "object", "embed", "svg", "math", "form", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.DROP:
            self.skip += 1
            return
        if self.skip or tag not in self.OK:
            return
        keep = ""
        for k, v in attrs:
            v = v or ""
            if k == "href" and tag == "a" and v.strip().lower().startswith(("http://", "https://")):
                keep += f' href="{html.escape(v, quote=True)}" rel="noopener noreferrer"'
            elif k == "class":
                keep += f' class="{html.escape(v, quote=True)}"'
        self.out.append(f"<{tag}{keep}>")

    def handle_endtag(self, tag):
        if tag in self.DROP:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in self.OK and tag != "br":
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))


def clean_html(s):
    p = _Clean()
    p.feed(s or "")
    p.close()
    return "".join(p.out)


def money(x):
    if x is None:
        return "—"
    x = round(x)
    return f"−${-x:,.0f}" if x < 0 else f"${x:,.0f}"


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def table(head, rows):
    h = "".join(f"<th>{x}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td{' class=n' if i else ''}>{v}</td>" for i, v in enumerate(r)) + "</tr>" for r in rows)
    return f"<div class=tablewrap><table><tr>{h}</tr>{b}</table></div>"


def render(res, sections, lang, summary="", quotes=()):
    t, c = L[lang], res["assumptions"]
    f, s, cmp = res["str_year"], res["ato_screen"], res["comparison"]
    e = html.escape
    before = [x for x in sections if len(x) > 2 and x[2] == "before"]
    after_s = [x for x in sections if not (len(x) > 2 and x[2] == "before")]

    def block(items):
        return "".join(f"<h2>{e(x[0])}</h2><div class=card>{clean_html(x[1])}</div>" for x in items)

    # text quoted from listings, web pages or documents: always shown as escaped plain text
    qt = "".join(f"<h2>{e(q[0])}</h2><div class=card><p class=small>{t['quote_note']}</p>"
                 f"<blockquote>{e(q[1])}</blockquote></div>" for q in quotes)

    rng = ""
    ends = {r["label"]: r for r in res["what_if"]}
    if "revenue_low" in ends and "revenue_high" in ends:
        lo, hi = ends["revenue_low"], ends["revenue_high"]
        rng = "<p><b>" + t["range_line"].format(lo=money(lo["gross_rent"]), hi=money(hi["gross_rent"]),
                                                a=money(lo["after_tax_cash"]), b=money(hi["after_tax_cash"])) + "</b></p>"

    def rate_of(k):
        return c["home_loan_rate"] if k == "mortgage" else c["alt_returns"][k]

    # ATO
    ato = f"<span class='tag {s['result']}'>{t[s['result']]}</span>"
    if res["str_year_if_fail"]:
        ato += f"<p>{t['if_fail']}:<b>{money(res['str_year_if_fail']['after_tax_cash'])}</b></p>"
    if s["result"] == "likely_fail" and f["tax"] > 0 and f["pre_tax_cash"] < 0:
        ato += f"<p class=warn>{t['red_tax']}</p>"
    # year
    rows = [(t["rev"], f["revenue"]), (t["levy"], -f["short_stay_levy"]), (t["plat"], -f["platform_fee"]),
            (t["mgmt"], -f["management"]), (t["direct"], -f["direct_costs"]), (t["hold"], -f["holding_costs"]),
            (t["interest"], -f["interest"]), (t["pre"], f["pre_tax_cash"]), (t["tax"], -f["tax"])]
    if f["effort_cost"]:
        rows.append((t["effort"], -f["effort_cost"]))
    rows.append((f"<b>{t['after']}</b>", f["after_tax_cash"]))
    yr = table(["", ""], [(k, money(v)) for k, v in rows if not (k == t["levy"] and v == 0)])
    yr = yr.replace("<tr><th></th><th></th></tr>", "")
    if round(f["first_year_after_tax_cash"]) != round(f["after_tax_cash"]):
        yr += f"<p class=small>{t['first']}:{money(f['first_year_after_tax_cash'])}</p>"
    yr += f"<p>{t['gross']} <b>{pct(res['yields']['gross'])}</b> · {t['netY']} <b>{pct(res['yields']['net_before_interest'])}</b></p>"
    yr += f"<p class=small>{t['net_def'].format(mgmt=pct(c['mgmt_fee']))}</p>"
    if f["loss_quarantined"]:
        yr += f"<p class=warn>{t['quar']}</p>"
    # comparison
    if c["mode"] == "buy":
        ch = (f"<p class=warn>{t['alt_disc']}</p><p>{t['upfront']}:<b>{money(cmp['upfront_cash'])}</b>({t['duty']} {money(cmp['stamp_duty_used'])},"
              f"{t['duty_src'][cmp['stamp_duty_source']]}) · {t['bookc']}:<b>{money(cmp['booking_cost_per_year'])}</b></p>")
        ch += table([t["alt"], t["be"]], [
            (f"{t[k]}({pct(rate_of(k))})",
             f"<b>{pct(v['breakeven_growth']) if v['breakeven_growth'] is not None else t['be_none']}</b>")
            for k, v in cmp["by_alternative"].items()])
        vl = cmp.get("vs_long_term_property")
        if vl:
            ch += (f"<h3>{t['vs_lt']}</h3><p>{t['lt_cash']}:<b>{money(vl['lt_year']['after_tax_cash'])}</b> · "
                   f"{t['diff_cash']}:<b>{money(vl['annual_cash_holiday_minus_lt'])}</b></p>")
            ch += table([t["lt_g"], t["h_need"]], [
                (pct(float(g)), f"<b>{pct(v['holiday_growth_needed']) if v['holiday_growth_needed'] is not None else t['be_none']}</b>")
                for g, v in vl["growth_refs"].items()])
    else:
        ch = (f"<p class=warn>{t['alt_disc']}</p><p>{t['sell_now']}:<b>{money(cmp['sell_now']['net_proceeds'])}</b> · "
              f"{t['lt_year']}:<b>{money(cmp['long_term_year']['after_tax_cash'])}</b></p>")

        def be(x):
            return pct(x) if x is not None else t["be_none"]
        ch += table([t["alt"], t["keep_sell"], t["lt_sell"]], [
            (f"{t[k]}({pct(rate_of(k))})", f"<b>{be(v['breakeven_growth_keep_vs_sell'])}</b>",
             f"<b>{be(v['breakeven_growth_long_term_vs_sell'])}</b>")
            for k, v in cmp["by_alternative"].items()])
        for k, v in cmp["by_alternative"].items():
            for g, r in v["scenarios"].items():
                ch += (f"<p class=small>{t[k]} · {t['wealth'].format(n=c['years'], g=pct(float(g)))}:"
                       f"{t['keep_str']} {money(r['keep_str'])} / {t['long_term']} {money(r['long_term'])} / {t['sell']} {money(r['sell_now'])}</p>")
    wi = ""
    if res["what_if"]:
        wi = f"<h2>{t['whatif']}</h2><div class=card>" + table(
            [t["wi_label"], t["wi_zone"], t["wi_cash"], t["wi_be"]],
            [(e(t.get(r["label"], r["label"])), t["zone_short"][r["ato"]], money(r["after_tax_cash"]),
              pct(r["breakeven_vs_deposit"]) if r["breakeven_vs_deposit"] is not None else t["be_none"])
             for r in res["what_if"]]) + "</div>"
    title = t["buy"] if c["mode"] == "buy" else t["own"]
    lines = list(t["disc"][:1]) + ([t["disc_loan"]] if c["loan"] else []) + list(t["disc"][1:])
    disc = "".join(f"<p class=small>{x}</p>" for x in lines)
    simp = ";".join(SIMPLIFICATIONS_ZH) if lang == "zh" else "; ".join(res["simplifications"])
    return f"""<!doctype html><html lang="{'zh-CN' if lang == 'zh' else 'en'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(t['title'])}</title><style>{CSS}</style></head><body>
<header><div class=wrap><h1>{e(t['title'])} · {e(title)}</h1><div>{date.today().isoformat()} · {money(c['price'])}</div></div></header>
<div class=wrap>
{f"<div class=card style='border-left:5px solid #0b6e74'>{clean_html(summary)}{rng}</div>" if summary or rng else ""}
{block(before)}
{qt}
<h2>{t['ato']}</h2><div class=card>{ato}</div>
<h2>{t['net']}</h2><div class=card>{yr}</div>
<h2>{t['cmp']}</h2><div class=card>{ch}</div>
{wi}
{block(after_s)}
<p class=small>{t['simp']}:{e(simp)}</p>
{disc}
<p class=small>{t['footer']}<a href="{e(c['video_url'])}">{e(c['video_url'])}</a></p>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--html")
    a = ap.parse_args()
    with open(a.input, encoding="utf-8") as fh:
        inp = json.load(fh)
    sections = inp.pop("report_sections", [])   # [[heading, html, "before"?], ...]
    summary = inp.pop("report_summary", "")
    quotes = inp.pop("report_quotes", [])      # [[heading, text quoted from a listing / page], ...]
    res = run(inp)
    sys.stdout.reconfigure(encoding="utf-8")
    json.dump(res, sys.stdout, ensure_ascii=False, indent=2, default=str)
    if a.html:
        with open(a.html, "w", encoding="utf-8") as fh:
            fh.write(render(res, sections, res["assumptions"]["lang"], summary, quotes))


if __name__ == "__main__":
    main()
