#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_report.py — auspptdd report generator (free public-data edition).

Reads ONE data.json (schema: SKILL.md "出报告" section / --schema) and writes a
self-contained HTML report with the fixed nine-section structure, the three-tier
"not detected / not covered / not available" wording with a mandatory NEXT STEP cell,
comparable cards scored on land / slope / condition with a data-completeness badge,
the buyer-view block (first offer / walk-away / confidence, $50k mortgage delta,
bank-valuation reminder, holding costs, school, commute), an inspection checklist,
solicitor / building-inspector brief templates, a desktop-vs-field count bar and a
footer with human time vs machine time.

usage:
  python gen_report.py --data data.json --out report.html [--lang zh|en] [--template ../templates/report.html]
  python gen_report.py --schema            # print the data.json field list and exit

Windows: the script forces UTF-8 on stdout/stderr and every open(); no PYTHONUTF8 needed.
No third-party packages.
"""
import sys, os, json, re, html, math, argparse, datetime, statistics

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_DEFAULT = "https://www.youtube.com/@shuailuo"
BOOKING = {"zh": "https://avocadowealth.com.au/free-consultation-team?ref=auspptdd", "en": "https://avocadowealth.com.au/home-english?ref=auspptdd"}

# ---------------------------------------------------------------- fixed strings (zh / en)
T = {
 "expand_all": ("全部展开", "Expand all"), "collapse_all": ("全部收起", "Collapse all"),
 "toolbar_hint": ("首屏是 3 分钟摘要;下面每一节点开看细节。", "The top block is the 3-minute summary; open each section below for detail."),
 "back": ("回到所属对话", "Back to the conversation"), "copy_title": ("复制对话标题", "Copy title"),
 "disclaimer": ("所有价格均为公开数据推算的<b>估计</b>,不是估值(valuation)。付费数据一律未使用,相应格子按固定口径留空并写明去哪拿。取数日期 {date}。",
                "Every price is an <b>estimate from public data</b>, not a valuation. No paid data was used; cells that need it say so and tell you where to get it. Data date {date}."),
 "summary_h": ("一页摘要", "One-page summary"), "range": ("我们的估计合理区间*", "Our estimated fair range*"),
 "max_risk": ("最大风险", "Biggest risk"), "offer_first": ("首次出价", "First offer"), "offer_walk": ("放手价", "Walk-away"),
 "offer_conf": ("把握程度", "Confidence"),
 "s1": ("1. 总览 Overview", "1. Overview"), "s2": ("2. 时间线与价格标尺 Timeline & price ruler", "2. Timeline & price ruler"),
 "s3": ("3. 风险体检 Hazard check", "3. Hazard check"), "s4": ("4. 土地 Land", "4. Land"),
 "s5": ("5. 可比成交 Comparables", "5. Comparables"), "s6": ("6. 未来价值 Future value", "6. Future value"),
 "s7": ("7. 市场 Market", "7. Market"), "s8": ("8. 下一步:问中介、买前必备、看房核对、给专业人士的 brief", "8. Next steps: agent questions, before you buy, inspection checklist, briefs"),
 "s9": ("9. 名词表 Glossary", "9. Glossary"),
 "photos": ("照片", "Photos"), "photo_none": ("本次没有拿到可核对的照片链接。", "No cross-checked photo link was obtained this run."),
 "photo_next": ("下一步:在你自己的浏览器按顺序打开 REA → Domain → property.com.au → onthehouse / Aussie → 中介官网,至少三项(地址、卧卫、土地、价格)一致才算同一套;把链接贴回来即可补判建材。(你自己)",
                "Next: open in your own browser, in order, REA → Domain → property.com.au → onthehouse / Aussie → the agent's site; three matching facts (address, beds/baths, land, price) confirm it is the same house. Paste the links back and the material judgement can be added. (you)"),
 "streetview": ("Google 街景(仅链接)", "Google Street View (link only)"),
 "paid_block": ("公开数据查不到这一项。它确实存在,拿到它有三条路:① 问销售中介;② 咨询持牌买家代理;③ 订阅付费数据(如 Cotality)。",
                "Not in public data. It exists, and there are three ways to get it: ① ask the selling agent; ② ask a licensed buyer's agent; ③ a paid data subscription (e.g. Cotality)."),
 "next_lbl": ("下一步", "Next"),
 "not_detected": ("未检出 ✓ 目前看风险较低", "Not detected ✓ low risk so far"), "uncovered": ("免费数据不覆盖", "Not covered by free data"),
 "cond": ("条件项", "Conditional"),
 "flood_cond_next": ("① 向 council 申请洪水信息,拿规划洪水位(FPL)与 1% AEP 水位,和房屋地板高度比(律师看 10.7 第 2 部分 / 你申请);② 两家保险公司按地址含洪水报价(你)。这两项没拿到之前,出价只能是条件出价。",
                     "① Get the council flood information (flood planning level and 1% AEP level) and compare with the floor level (solicitor via s10.7 part 2 / you); ② two insurers' quotes for this address including flood (you). Until both are in hand, any offer is conditional."),
 "paid_block_item": ("<b>{item}</b> · 公开数据查不到这一项。它确实存在,拿到它有三条路:① 问销售中介;② 咨询持牌买家代理;③ 订阅付费数据(如 Cotality)。",
                     "<b>{item}</b> · Not in public data. It exists, and there are three ways to get it: ① ask the selling agent; ② ask a licensed buyer's agent; ③ a paid data subscription (e.g. Cotality)."),
 "foot_time3": ("人介入约 {h} 分钟 · 机器活跃约 {a} 分钟 · 墙钟约 {w} 分钟。", "Human time about {h} min · active machine time about {a} min · wall clock about {w} min."),
 "gallery_public": ("公开版只放小图与链接;大图请在挂牌页看。", "Public edition shows thumbnails and links only; full-size photos are on the listing page."),
 "gallery_link": ("在挂牌页看全部照片 →", "See all photos on the listing →"),
 "ba_h": ("同角度翻新前后对比(自用版)", "Same-angle before / after (internal edition)"),
 "chart_src": ("数据表(出处与原始数值)", "Data table (source and raw values)"),
 "tiles_lead": ("一眼看:红 = 命中(否决或条件项),橙 = 适用/要留意,绿 = 未检出,灰 = 免费数据查不到。点开看结果与下一步。", "At a glance: red = hit (veto or conditional), orange = applies / watch, green = not detected, grey = not in free data. Open a tile for the result and next step."),
 "scatter_h": ("可比一图:土地面积 × 成交价", "Comparables in one chart: land area × sale price"),
 "scatter_note": ("点色 = 三项打分结论(红 优于 / 金 相当 / 绿 逊于);粗环 = 夹板;★ = 标的(标价);绿带 = 合理区间。", "Dot colour = three-score verdict (red superior / gold close / green inferior); thick ring = bookend; ★ = subject at list price; green band = fair range."),
 "dom_bars_h": ("在市时长对比", "Days on market, compared"), "dom_this": ("本套(约)", "This property (approx.)"), "dom_sub": ("区均(不是本套)", "Suburb median (not this one)"),
 "mort_h": ("三个价位的月供", "Repayment at the three prices"), "mort_list": ("标价", "List"),
 "ruler_more": ("›{cap} 还有 {n} 笔", "{n} more above {cap}"),
 "future_chips": ("路径一览", "Paths at a glance"),
 "priceline_h": ("我该出多少:所有价位放在一条轴上", "What to offer: every price on one axis"),
 "priceline_note": ("绿带 = 合理区间;红线 = 标价;虚线 = 首次出价 / 放手价;字母 = 可比成交(见第 5 节);灰带 = Domain 免费估值区间(模型值,只作对照)。", "Green band = fair range; red line = list; dashed = first offer / walk-away; letters = comparables (section 5); grey band = Domain free estimate (model value, for reference only)."),
 "tiers_h": ("三档价位", "Three price tiers"), "tier_th": (("档", "价位", "依据"), ("Tier", "Price", "Basis")),
 "tier_first": ("首次出价", "First offer"), "tier_fair": ("合理区间", "Fair range"), "tier_walk": ("放手价(上限,不是建议价)", "Walk-away (ceiling, not a target)"),
 "matrix_h": ("可比一览(点字母看详情)", "Comparables at a glance (letters open the cards)"),
 "matrix_th": (("#", "地址", "成交", "价", "P/LV", "距离", "土地", "坡度", "房况", "完整度"), ("#", "Address", "Sold", "Price", "P/LV", "Dist", "Land", "Slope", "Cond.", "Compl.")),
 "map_h": ("可比相对位置(以标的为中心,圈 = 500 / 1,000 / 1,500 m)", "Comparables around the subject (rings = 500 / 1,000 / 1,500 m)"),
 "street_scatter_h": ("同街成交:时间 × 价格(气泡 = 土地面积)", "Same-street sales: date × price (bubble = land area)"),
 "tiles_grey": ("以下 {n} 项免费数据查不到(点开看去哪拿)", "{n} items with no free data (open to see where to get them)"),
 "coverage": ("22 项核查覆盖度", "Coverage of the checks"), "cov_hit": ("命中 / 条件", "hit / conditional"), "cov_watch": ("要留意", "watch"), "cov_ok": ("未检出", "not detected"), "cov_none": ("免费数据无", "no free data"),
 "profile_flat": ("地块平坦:街面 {s} m → 后边界 {r} m,落差 {f} m;剖面图省略。", "Flat site: street {s} m → rear {r} m, fall {f} m; profile chart omitted."),
 "tl_strip_note": ("按真实时间比例;红点 = 现在挂牌;问号 = 待核实的记录。", "True time scale; red = current listing; ? = record to verify."),
 "hazard_rule": ("规则:主流洪水区 / High–Medium 分区命中 = 否决;Overland Flow / Low(PMF)命中 = 条件项(固定两个下一步:规划洪水位 vs 地板高度;保险报价);其余风险只换算成价格调整。「未检出」只在图层覆盖该 council 时写,并配一个现场/合同里确认的小动作。",
                 "Rule: mainstream flood / High–Medium precinct hit = veto; Overland Flow / Low (PMF) hit = conditional (two fixed next steps: flood planning level vs floor level; insurance quote); every other risk becomes a price adjustment. 'Not detected' is written only where the layer covers this council, with a small on-site / contract check attached."),
 "applies": ("适用", "Applies"), "paid_short": ("公开数据无(见下一步)", "Not in public data (see next step)"),
 "th_layer": ("项", "Item"), "th_result": ("结果", "Result"), "th_source": ("权威来源 / 图层", "Authority / layer"), "th_date": ("查询日期", "Queried"),
 "th_note": ("说明", "Notes"), "th_next": ("下一步(谁做 · 做什么 · 在哪做)", "Next step (who · what · where)"),

 "timeline_th": (("时间", "事件", "来源"), ("Date", "Event", "Source")),
 "dom_h": ("在市天数与调价史", "Days on market & price history"),
 "dom_approx": ("按首挂月份推算约 {m} 个月({basis})", "About {m} months from the first-listed month ({basis})"),
 "dom_suburb": ("区均在市天数 {d} 天({src}),不是本套的天数", "Suburb median days on market {d} ({src}); not this property's"),
 "dom_unverified": ("挂牌时长未验证 ?", "Listing duration unverified ?"),
 "ruler_lead": ("<b>价格标尺</b>——{window} 该郊区非分层房屋官方成交 {n} 笔,中位 {median};标价 {list} 位于其中:",
                "<b>Price ruler</b> — {n} official non-strata house sales in {window}, median {median}; the list price {list} sits here:"),
 "ruler_me": ("标价 {list}(其中 {pct:.0f}% 的成交比它低)", "List {list} ({pct:.0f}% of sales below it)"),
 "ruler_note": ("灰点 = 每笔官方成交(滞后约 2 个月);红线 = 标价。", "Grey dots = official sales (about 2 months' lag); red line = list price."),
 "lv_h": ("官方地价 5 年史(基准日 7 月 1 日)", "Official land value, 5 years (base date 1 July)"),
 "street_sales_h": ("同街官方成交记录(每物业最近一笔)", "Official sales on the same street (latest per property)"),
 "profile_h": ("沿进深的地形剖面", "Ground profile along the depth"),
 "comp_lead": ("可比先于区间:先逐张打分,再定夹板,最后出合理区间。标签只按三项打分——土地 / 坡度与街面侧 / 房况(建年、面积、建材、翻新);价格只当结果摆旁边。默认只展开「相当」与两块夹板,其余点开看。",
               "Comparables come before the range: score each card, pick the bookends, then set the range. Labels come only from three scores — land / slope & street side / condition (year, area, material, renovation); price is shown beside as a result. Only 'Close' cards and the two bookends are open by default."),
 "v_sup": ("优于", "Superior"), "v_close": ("相当", "Close"), "v_inf": ("逊于", "Inferior"),
 "bk_upper": ("上夹板", "Upper bookend"), "bk_lower": ("下夹板", "Lower bookend"),
 "completeness": ("数据完整度", "Data completeness"),
 "cg_basic": ("基本", "Basics"), "cg_price": ("价格与比率", "Price & ratios"), "cg_cmp": ("与标的比较(三项打分)", "Versus subject (three scores)"), "cg_verdict": ("结论", "Verdict"),
 "sc_land": ("土地", "Land"), "sc_slope": ("坡度/街面侧", "Slope/street side"), "sc_cond": ("房况", "Condition"),
 "sc_better": ("优", "better"), "sc_same": ("同", "same"), "sc_worse": ("逊", "worse"), "sc_unknown": ("未知", "unknown"),
 "bk_low_warn": ("该夹板数据完整度低于 5/8,不符合夹板要求;区间已加宽并说明。", "This bookend has completeness below 5/8 and does not qualify; the range was widened and the reason stated."),
 "plv_h": ("成交价 / 官方地价 倍数交叉检验", "Sale price ÷ land value cross-check"),
 "pricing_h": ("合理区间怎么来的", "How the range was derived"),
 "mortgage": ("每差 {step} 对月供的影响:约 {delta}/月(假设利率 {rate:.2f}%、{years} 年本息同还;公式 P·r/(1−(1+r)^−n),r = 月利率,n = 月数)。",
              "Each {step} of price moves the repayment by about {delta}/month (assumes {rate:.2f}% p.a., {years}-year principal & interest; P·r/(1−(1+r)^−n), r = monthly rate, n = months)."),
 "bank_val": ("银行估值可能低于成交价:坡地、带租约、长时间在市、原装房都会让估价师保守;差额要用自有资金补。出价前让 broker 做一次桌面估值预审。(你自己 / broker)",
              "The bank valuation may come in below the sale price: sloping land, a lease in place, a long campaign and original condition all make valuers conservative; any gap is cash from you. Ask your broker for a desktop valuation before you offer. (you / broker)"),
 "holding_h": ("持有成本(估算)", "Holding costs (estimate)"), "school_h": ("学区与通勤", "School catchment & commute"),
 "future_th": (("路径", "结论", "依据(条文)", "下一步"), ("Path", "Conclusion", "Basis (clause)", "Next step")),
 "vac_h": ("空置率", "Vacancy rate"), "som_h": ("在售库存", "Stock on market"), "growth_h": ("长期增长(官方成交中位价,3 年窗口平滑)", "Long-run growth (official sale medians, 3-year window)"),
 "growth_th": (("周期", "起点窗口中位", "当前窗口中位", "累计", "年化"), ("Period", "Start-window median", "Current-window median", "Cumulative", "Annualised")),
 "thirty": ("30 年", "30 years"), "ask_h": ("要价与租金(周度,噪声大,只看方向)", "Asking prices & rents (weekly, noisy, direction only)"),
 "yearly_h": ("逐年官方成交中位(笔数)", "Official sale median by year (count)"),
 "q_h": ("问中介的问题", "Questions for the agent"), "bb_h": ("买前必备", "Before you buy"), "bb_th": (("项", "为什么", "谁做"), ("Item", "Why", "Who")),
 "ck_h": ("看房核对单", "Inspection checklist"), "brief_sol": ("给律师的 brief(可直接发)", "Brief for your solicitor (ready to send)"),
 "brief_insp": ("给验房师的 brief(可直接发)", "Brief for your building & pest inspector (ready to send)"),
 "manual_h": ("要人做的清单(汇总)", "Everything that still needs a person (summary)"),
 "countbar": ("本报告替你完成了 <b>{n}</b> 项桌面核查;还有 <b>{m}</b> 项要在现场、合同、专业人士处完成(清单见第 8 节)。桌面尽调是前一半,现场与执行是后一半。",
              "This report completed <b>{n}</b> desktop checks for you; <b>{m}</b> items remain for the site, the contract and professionals (list in section 8). Desktop research is the first half; the field and execution are the second."),
 "foot_time": ("人介入的时间约 {h} 分钟;机器总耗时约 {mc} 分钟。", "Human time about {h} min; machine time about {mc} min."),
 "foot_gen": ("由 auspptdd(公开数据免费版)生成 · 取数日期 {date} · 本报告不是估值,也不是财务、法律或贷款建议。", "Generated by auspptdd (free public-data edition) · data date {date} · not a valuation, not financial, legal or lending advice."),
 "attrib": ("本工具由罗帅(Shuai Luo,悉尼买家代理)出品,免费开源。这个工具背后的思路,罗帅在 YouTube「澳洲罗帅」这期视频里讲了:{video}",
            "Made by Shuai Luo, a Sydney buyer's agent, free and open source. The thinking behind this tool is explained in this video on his YouTube channel 「澳洲罗帅」: {video}"),
 "n_more": (",另有 {n} 项(见上)", ", and {n} more (listed above)"),
 "needs_person": ("这份报告做完了桌面上能做的部分。还要人去做的是:{list}。这些你可以自己做,也可以请律师、验房师或持牌买家代理帮忙。",
                  "This report covers the desk research. What still needs a person: {list}. You can do these yourself or bring in a solicitor, a building inspector or a licensed buyer's agent."),
 "booking": ("如果你想让罗帅团队帮你做这几步,可以预约 30 分钟 1 对 1 免费购房策略体检:{url}(买家代理服务由 Avocado Wealth 提供,NSW 持牌,牌照号 10109450)。",
             "If you'd like Shuai Luo's team to handle these steps, you can talk to us: {url} (buyer's agent services provided by Avocado Wealth, NSW licence 10109450)."),
 "material_from_photo": ("从照片判读", "judged from photos"), "unknown": ("未知", "unknown"),
 "ask_agent": ("要问中介", "ask the agent"),
 "blockers_h": ("本次运行的卡点", "Blockers hit in this run"),
 "nav_list": ("标价", "List"), "nav_range": ("合理区间(估)", "Fair range (est.)"),
 "f_beds": ("卧", "bd"), "f_baths": ("卫", "ba"), "f_cars": ("车", "car"), "f_land": ("m² 土地", "m² land"), "f_floor": ("m² 建筑", "m² floor"), "f_built": ("年建", "built"),
 "k_list": ("标价", "List price"), "k_range": ("合理区间(估)", "Fair range (est.)"), "k_walk": ("放手价", "Walk-away"), "k_status": ("现状", "Status"),
 "k_dom": ("挂牌", "Listing"), "k_lv": ("官方地价", "Land value"), "k_dom_txt": ("{basis};约 {m} 个月", "{basis}; about {m} months"), "k_dom_sub": (";区均约 {d} 天", "; suburb median about {d} days"),
 "one_line": ("一句话", "In one line"),
 "photo_credit": ("照片来自 {src},版权归原摄影师与销售中介;本页只链接显示,不下载、不转存。", "Photos from {src}; copyright remains with the photographer and the selling agent; linked for display only, never downloaded or re-hosted."),
 "photo_placeholder": ("本次没有拿到可展示的照片。", "No displayable photos were obtained this run."),
 "range_how": ("合理区间怎么来的", "How the fair range was set"),
 "tl_h": ("时间线", "Timeline"),
 "ruler_note2": ("灰点 = 每笔官方成交(滞后约 2 个月);绿带 = 本报告的合理区间;红线 = 标价。", "Grey dots = official sales (about 2 months' lag); green band = this report's fair range; red line = list price."),
 "v_unk": ("未知", "Unknown"),
 "bk_unk_warn": ("三项打分全部未知,不能作夹板。", "All three scores are unknown; this card cannot be a bookend."),
 "growth_kind": ({"house": "独立屋", "unit": "公寓/单元", "building": "本楼"}, {"house": "House", "unit": "Unit", "building": "This building"}),
 # unit-mode variants: t(k) picks k + "_u" automatically when UNIT is on
 "s4_u": ("4. 母地块与楼栋 Parent lot & building", "4. Parent lot & building"),
 "f_land_u": ("m² 产权面积", "m² strata lot"),
 "k_lv_u": ("母地块地价", "Parent-lot land value"), "k_lv_val": ("{v}(份额需人)", "{v} (entitlement: needs a person)"),
 "sc_land_u": ("面积与车位", "Area & cars"), "sc_slope_u": ("楼层·朝向·景观", "Level·aspect·view"),
 "comp_lead_u": ("可比先于区间:先逐张打分,再定夹板,最后出合理区间。标签只按三项打分——面积与车位 / 楼层·朝向·景观 / 房况(建年、翻新、楼栋状况);价格只当结果摆旁边。排序:同竖列(同户型、同朝向)成交最优先,其次同楼,再次同郊区同卧室数、建筑面积 ±20%、18 个月内。默认只展开「相当」与两块夹板,其余点开看。",
                 "Comparables come before the range: score each card, pick the bookends, then set the range. Labels come only from three scores — area & cars / level·aspect·view / condition (year, renovation, building condition); price is shown beside as a result. Ranking: same-stack sales (same floor plan, same aspect) first, then the same building, then the same suburb with the same bedrooms, floor area within ±20% and sold within 18 months. Only 'Close' cards and the two bookends are open by default."),
 "bk_low_warn_u": ("该夹板数据完整度低于 4/8,不符合夹板要求;区间已加宽并说明。", "This bookend has completeness below 4/8 and does not qualify; the range was widened and the reason stated."),
 "scatter_h_u": ("可比一图:建筑面积 × 成交价", "Comparables in one chart: floor area × sale price"),
 "matrix_th_u": (("#", "地址", "成交", "价", "面积 m²", "距离", "楼层", "车位", "房况", "完整度"), ("#", "Address", "Sold", "Price", "Floor m²", "Dist", "Level", "Cars", "Cond.", "Compl.")),
 "street_scatter_h_u": ("同街/同楼成交:时间 × 价格(气泡 = 建筑面积)", "Same-street sales: date × price (bubble = floor area)"),
 "lv_h_u": ("母地块地价 5 年史(整栋基地,不是本单元)", "Parent-lot land value, 5 years (whole site, not this unit)"),
 "fig_a": ("图 A", "Figure A"), "profile_h_u": ("图 B", "Figure B"),
 "ruler_lead_u": ("<b>价格标尺</b>——{window} 该郊区成交 {n} 笔(口径见数据说明),中位 {median};标价 {list} 位于其中:",
                  "<b>Price ruler</b> — {n} sales in {window} (scope as noted in the data), median {median}; the list price {list} sits here:"),
 "u_level": ("楼层", "Level"), "u_cars": ("车位", "Cars"), "u_aspect": ("朝向", "Aspect"), "u_levies": ("Strata 费", "Levies"),
 "u_floor": ("建筑", "Floor"), "u_pm2": ("$/m² 建筑", "$/m² floor"),
}
DISCLAIMER_END = (
 ("这是我们自己买房时会用的工具,仅供参考。本报告是一般信息,未结合您的个人情况。",
  "This is a tool we use in our own property purchases, provided for reference only. It is general information and does not take your personal circumstances into account."),
 ("本报告不构成个人投资建议。具体请自行分析或寻求持牌专业人士意见。",
  "This report is not personal investment advice. Please do your own analysis or seek advice from a licensed professional."),
 ("借贷测算只是示意,以银行或持牌贷款经纪的正式评估为准。",
  "Borrowing figures are illustrative only; a lender's or licensed broker's formal assessment is what counts."),
 ("房源图片版权归原权利人。本报告只提供房源链接与缩略图,用于识别房源。",
  "Listing photos belong to their copyright owners. This report only links to listings and shows thumbnails to identify the property."),
 ("数据来自报告所列公开来源,取数日期见各条,可能有延迟或误差;需要付费订阅的数据未使用,相应字段留空。",
  "Data comes from the public sources listed, with retrieval dates shown; it may be delayed or contain errors. Paid-subscription data is not used and those fields are left blank."),
)
# default status-card labels when the data gives none (house / unit)
DEFAULT_CARDS = {
 "house": (("洪水 Flood", "Flood"), ("山火 Bushfire", "Bushfire"), ("坡地类别 Landslip", "Landslip category"), ("实测坡度 Slope", "Measured slope"), ("开发潜力 Development", "Development potential")),
 "unit": (("洪水(地库/大堂)", "Flood (basement / lobby)"), ("山火", "Bushfire"), ("噪音与干道", "Noise & arterial roads"), ("Strata 体检", "Strata health check"), ("规划与供应", "Planning & supply")),
}
LANG = "zh"
UNIT = False   # unit (strata) mode; set by build() from is_unit(d)
def _k(k):
    return k + "_u" if UNIT and (k + "_u") in T else k
def t(k, **kw):
    v = T[_k(k)][0 if LANG == "zh" else 1]
    return v.format(**kw) if kw else v
def tt(k):  # tuple variant
    return T[_k(k)][0 if LANG == "zh" else 1]
_UNIT_WORDS = re.compile(r"\b(?:unit|apartment|flat)s?\b|公寓|单元", re.I)
def is_unit(d):
    """True for strata units: subject.title_type == strata, a unit-like dwelling word, or an SP (strata plan) number in lot_dp."""
    s = d.get("subject") or {}
    if str(s.get("title_type") or "").strip().lower() == "strata": return True
    if _UNIT_WORDS.search(str(s.get("dwelling") or "")): return True
    return bool(re.search(r"(?<![A-Za-z])SP\s*\d", str(s.get("lot_dp") or "")))

# ---------------------------------------------------------------- defaults
DEFAULT_CHECKLIST = {
 "zh": ["坡:从街面到房门走一遍,数台阶,看雨水往哪流、有没有挡土墙裂缝或倾斜",
        "水:屋檐、地下室/底层墙角有没有水渍、霉斑、返潮味;雨后再来一次最好",
        "味:进门的味道(霉、烟、宠物、新漆盖味)",
        "声:在院子里站 5 分钟听干道、飞机、邻居;早晚各一次",
        "邻居:两侧与后院的房况、车、狗、加建;街上停车",
        "挡土与地基:外墙裂缝走向、门窗能否顺畅开关、地面是否倾斜",
        "潮气与白蚁:木地板弹性、踢脚线、屋顶空间入口",
        "建材:外墙是砖 / 木板 / fibro / 渲染?屋顶瓦还是彩钢?拍照留证"],
 "en": ["Slope: walk from the street to the front door, count the steps, see where rainwater goes, check retaining walls for cracks or lean",
        "Water: stains, mould or damp smell at eaves and lower wall corners; come back after rain if you can",
        "Smell: what you notice at the door (mould, smoke, pets, fresh paint covering something)",
        "Sound: stand in the yard for 5 minutes for traffic, aircraft, neighbours; morning and evening",
        "Neighbours: condition of both sides and the rear, cars, dogs, extensions; street parking",
        "Retaining and footings: direction of wall cracks, whether doors and windows run freely, sloping floors",
        "Damp and termites: springy floorboards, skirtings, roof-space access",
        "Materials: brick / weatherboard / fibro / render walls? tile or metal roof? photograph it"],
}
DEFAULT_BEFORE_BUY = {
 "zh": [("合同 + Section 10.7 规划证书", "核对洪水、山火、滑坡、heritage 标注与本报告一致;条文按现行版复核", "律师"),
        ("Building & Pest 报告", "结构、潮气、白蚁、屋顶、挡土;原装房重点查石棉", "验房师"),
        ("租约副本(若有)", "固定期还是周期;租金是否含水电;能否空置交割", "中介 → 律师"),
        ("银行估值 / 贷款预批", "估值可能低于成交价,差额自备", "broker"),
        ("雨水 / 岩土(坡地)", "排水、地基、挡土;加建前岩土评估", "工程师(按需)"),
        ("费用清单", "印花税、律师费、B&P、过户、保险、搬家;翻新报价(若要对标更高档可比)", "你自己")],
 "en": [("Contract + Section 10.7 planning certificate", "Confirm flood, bushfire, landslip and heritage notations match this report; re-check clauses against the current version", "solicitor"),
        ("Building & pest report", "Structure, damp, termites, roof, retaining; asbestos for original-condition houses", "inspector"),
        ("Copy of the lease (if any)", "Fixed or periodic; utilities included; vacant possession possible", "agent → solicitor"),
        ("Bank valuation / pre-approval", "Valuation may come in below price; shortfall is your cash", "broker"),
        ("Stormwater / geotech (sloping sites)", "Drainage, footings, retaining; geotech before any extension", "engineer (if needed)"),
        ("Cost list", "Stamp duty, legal, B&P, conveyancing, insurance, moving; renovation quotes if you plan to match the higher comparables", "you")],
}

# unit (strata) defaults — used only in unit mode; the house defaults above are unchanged
DEFAULT_CHECKLIST_UNIT = {
 "zh": ["大堂与电梯:等候时间、维护记录牌、地面与墙面状况",
        "地库:墙脚水渍、积水线、排水沟淤积;本套车位有没有进水痕迹",
        "公共部分缺陷:外墙与车库裂缝、外墙板(cladding)类型、阳台防水(渗水、瓷砖空鼓、栏杆锈)",
        "噪音:关窗站 5 分钟听干道车流;早晚各一次",
        "朝向与景观:看邻近楼栋或在建工地会不会挡光、挡景",
        "垃圾房、自行车房、储物间:位置、是否整洁、本套储物是否在产权内",
        "水:屋内墙角、窗框、湿区有没有水渍、霉斑、返潮味",
        "味:进门的味道(霉、烟、宠物、新漆盖味)",
        "声:邻居、上下楼、电梯与管道噪音",
        "邻居与楼栋氛围:走廊、公共区维护、短租痕迹"],
 "en": ["Lobby and lifts: wait times, maintenance notices, condition of floors and walls",
        "Basement: water marks, tide lines, blocked drains; any sign the car space has flooded",
        "Common-property defects: cracking in the façade and car park, cladding type, balcony waterproofing (leaks, drummy tiles, rusting balustrades)",
        "Noise: stand 5 minutes with the windows closed and listen for the arterial road; morning and evening",
        "Aspect and view: could neighbouring towers or construction sites block light or view",
        "Bin room, bike room, storage: location, upkeep, whether this unit's storage is on title",
        "Water: stains, mould or damp smell at wall corners, window frames, wet areas",
        "Smell: what you notice at the door (mould, smoke, pets, fresh paint covering something)",
        "Sound: neighbours, floors above and below, lifts and plumbing",
        "Neighbours and building feel: corridors, common-area upkeep, signs of short stays"],
}
DEFAULT_BEFORE_BUY_UNIT = {
 "zh": [("Strata 报告(NSW s 184 证书 / WA precontractual disclosure)", "全面看 strata 状况:欠费、纠纷、在办工程", "你 → strata 查档 / 律师"),
        ("Levies 历史与维修基金余额", "近 3–5 年 levies 走势、special levy、capital works fund 余额", "strata 查档"),
        ("By-laws", "宠物、短租、装修(地板、湿区)限制", "律师"),
        ("楼栋缺陷与保险理赔记录", "已知缺陷、索赔、诉讼;法定保修是否还在期内", "strata 查档 / 律师"),
        ("Cladding 状况", "是否有可燃外墙板,整改计划与费用", "strata 查档"),
        ("保险估值", "楼栋保险是否足额、免赔额多少", "strata 查档"),
        ("10 年资本工程计划", "大额维修(电梯、外立面、防水)排在哪年、要多少钱", "strata 查档"),
        ("费用清单", "印花税、律师费、strata 报告、验房、过户、保险、搬家", "你自己")],
 "en": [("Strata report (NSW s 184 certificate / WA precontractual disclosure)", "Overall strata position: arrears, disputes, works in progress", "you → strata search / solicitor"),
        ("Levies history and sinking-fund balance", "Levy trend over 3–5 years, special levies, capital works fund balance", "strata search"),
        ("By-laws", "Pets, short stays, renovation limits (floors, wet areas)", "solicitor"),
        ("Building defects and insurance claims", "Known defects, claims, litigation; whether statutory warranties still run", "strata search / solicitor"),
        ("Cladding status", "Any combustible cladding, remediation plan and cost", "strata search"),
        ("Insurance valuation", "Is the building insured for full replacement; what is the excess", "strata search"),
        ("10-year capital works plan", "When the big items (lifts, façade, waterproofing) fall due and what they cost", "strata search"),
        ("Cost list", "Stamp duty, legal, strata report, inspection, conveyancing, insurance, moving", "you")],
}
BB_FLOOD_UNIT = {"zh": ("两家保险公司报价(含洪水)", "洪水卡是条件项:按地址拿含洪水的报价,并问 strata 保险是否承保洪水", "你"),
                 "en": ("Two insurer quotes including flood", "The flood card is conditional: get address-level quotes including flood and ask whether the strata policy covers flood", "you")}

def money(v):
    try: return "$%s" % format(int(round(float(v))), ",")
    except Exception: return "—"
def esc(s): return html.escape("" if s is None else str(s))
def num(s):
    try: return float(re.sub(r"[^0-9.\-]", "", str(s)) or 0)
    except Exception: return 0.0
def paid(slug, item=None):
    # fixed wording, no link (slug kept in the signature for old callers)
    body = t("paid_block_item", item=esc(item)) if item else t("paid_block")
    return '<div class="paid">%s</div>' % body
def nextcell(text):
    return '<span class="next"><b>%s:</b>%s</span>' % (t("next_lbl"), esc(text)) if text else ""
def cls_of(status):
    return {"ok": "ok", "warn": "warn", "bad": "bad", "na": "na", "cond": "cond"}.get(status, "")

# ---------------------------------------------------------------- inline SVG charts (no libraries; colours from the page tokens)
def _nice(v):
    return ("%.1fM" % (v / 1e6)) if abs(v) >= 1e6 else (("%.0fk" % (v / 1e3)) if abs(v) >= 1e3 else ("%g" % v))
def svg_line(series, labels, ylab="", fmt=None, w=720, h=220, names=None, pct=False, hline=None):
    """series: list of lists of numbers (None allowed); labels: x labels (same length). 1 series = brand colour, 2 = c1/c2 + legend."""
    fmt = fmt or _nice
    pl, pr, pt, pb = 46, 12, 14, 30
    vals = [v for sr in series for v in sr if v is not None] + ([hline[1]] if hline else [])
    if not vals: return ""
    lo, hi = min(vals), max(vals)
    if lo == hi: lo, hi = lo * 0.9, hi * 1.1 or 1
    pad = (hi - lo) * 0.08; lo -= pad; hi += pad
    if pct and lo < 0: lo = 0
    n = max(len(x) for x in series)
    X = lambda i: pl + (w - pl - pr) * (i / max(1, n - 1))
    Y = lambda v: pt + (h - pt - pb) * (1 - (v - lo) / (hi - lo))
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="none" style="width:100%%;height:auto;aspect-ratio:%d/%d">' % (w, h, w, h)]
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (pl, w - pr, Y(v), Y(v), pl - 6, Y(v) + 4, (("%.1f%%" % v) if pct else _nice(v))))
    step = max(1, n // 6)
    for i in range(0, n, step):
        if i < len(labels): out.append('<text x="%.1f" y="%d" class="tick" text-anchor="middle">%s</text>' % (X(i), h - 8, esc(labels[i])))
    cols = ["var(--c1)", "var(--c2)"]
    for si, sr in enumerate(series):
        pts = [(X(i), Y(v)) for i, v in enumerate(sr) if v is not None]
        if not pts: continue
        out.append('<polyline fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round" points="%s"/>' % (cols[si % 2], " ".join("%.1f,%.1f" % q for q in pts)))
        lx, ly = pts[-1]; lv = [v for v in sr if v is not None][-1]
        out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" stroke="var(--card)" stroke-width="2"/>' % (lx, ly, cols[si % 2]))
        out.append('<text x="%.1f" y="%.1f" class="lab" text-anchor="end">%s</text>' % (lx - 8, ly - 8, ("%.2f%%" % lv) if pct else fmt(lv)))
        for i, v in enumerate(sr):
            if v is not None: out.append('<circle cx="%.1f" cy="%.1f" r="7" fill="transparent"><title>%s: %s</title></circle>' % (X(i), Y(v), esc(labels[i]) if i < len(labels) else i, ("%.2f%%" % v) if pct else fmt(v)))
    if hline:
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--bad)" stroke-width="2" stroke-dasharray="5 3"/><text x="%d" y="%.1f" class="lab" text-anchor="start" fill="var(--bad)">%s</text>' % (pl, w - pr, Y(hline[1]), Y(hline[1]), pl + 4, Y(hline[1]) - 5, esc(hline[0])))
    if names and len(series) > 1:
        out.append('<g class="legend">' + "".join('<rect x="%d" y="2" width="12" height="3" fill="%s"/><text x="%d" y="7" class="tick">%s</text>' % (pl + 90 * i, cols[i % 2], pl + 16 + 90 * i, esc(nm)) for i, nm in enumerate(names)) + '</g>')
    out.append('</svg>')
    return "".join(out)
def svg_bars(values, labels, fmt=None, w=720, h=200, highlight_last=True, baseline_zero=True):
    fmt = fmt or _nice; tfmt = _nice
    pl, pr, pt, pb = 46, 12, 22, 30
    vals = [v for v in values if v is not None]
    if not vals: return ""
    hi = max(vals) * 1.12; lo = 0 if baseline_zero else min(vals) * 0.9
    n = len(values); slot = (w - pl - pr) / n; bw = min(44, slot * 0.6)
    Y = lambda v: pt + (h - pt - pb) * (1 - (v - lo) / (hi - lo))
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="none" style="width:100%%;height:auto;aspect-ratio:%d/%d">' % (w, h, w, h)]
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (pl, w - pr, Y(v), Y(v), pl - 6, Y(v) + 4, tfmt(v)))
    for i, v in enumerate(values):
        if v is None: continue
        x = pl + slot * i + (slot - bw) / 2; y = Y(v); hh = Y(lo) - y
        col = "var(--c1)" if (highlight_last and i == n - 1) else "var(--c1-soft)"
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"><title>%s: %s</title></rect>' % (x, y, bw, max(1, hh), col, esc(labels[i]), fmt(v)))
        out.append('<text x="%.1f" y="%.1f" class="lab" text-anchor="middle">%s</text>' % (x + bw / 2, y - 5, fmt(v)))
        out.append('<text x="%.1f" y="%d" class="tick" text-anchor="middle">%s</text>' % (x + bw / 2, h - 8, esc(labels[i])))
    out.append('</svg>')
    return "".join(out)
def svg_hbars(rows, fmt=None, w=720):
    """rows: [(label, value, note[, kind])] -> horizontal bars, value in %, zero baseline. kind house|unit|building picks the bar colour."""
    fmt = fmt or (lambda v: "%.1f%%" % v)
    vals = [r[1] for r in rows if r[1] is not None]
    if not vals: return ""
    hi = max(max(vals), 0.1) * 1.15; rh = 26; h = rh * len(rows) + 10; pl = 120
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="none" style="width:100%%;height:auto;aspect-ratio:%d/%d">' % (w, h, w, h)]
    for i, row in enumerate(rows):
        lab, v, note = row[:3]; kind = row[3] if len(row) > 3 else None
        y = 6 + rh * i
        out.append('<text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (pl - 8, y + 14, esc(lab)))
        if v is None: out.append('<text x="%d" y="%.1f" class="tick">%s</text>' % (pl, y + 14, esc(note or "—"))); continue
        bw = (w - pl - 70) * (v / hi)
        out.append('<rect x="%d" y="%.1f" width="%.1f" height="16" rx="3" fill="%s"><title>%s: %s</title></rect><text x="%.1f" y="%.1f" class="lab">%s</text>' % (pl, y + 2, max(2, bw), KIND_COL.get(kind, "var(--c1)"), esc(lab), fmt(v), pl + bw + 6, y + 14, fmt(v)))
    out.append('</svg>')
    return "".join(out)
KIND_COL = {"house": "var(--c1)", "unit": "var(--c2)", "building": "var(--accent)"}
def kind_legend(kinds):
    """small HTML legend for growth bars when more than one kind is present"""
    ks = [k for k in ("house", "unit", "building") if k in kinds]
    if len(ks) < 2: return ""
    names = tt("growth_kind")
    return '<p class="note kleg">%s</p>' % " ".join('<span style="white-space:nowrap"><i style="display:inline-block;width:12px;height:10px;border-radius:2px;background:%s;margin-right:4px;vertical-align:-1px"></i>%s</span>&nbsp;' % (KIND_COL[k], names[k]) for k in ks)
def letter(i): return chr(65 + i) if i < 26 else "Z%d" % (i - 25)
def svg_priceline(points, bands, w=720, h=128):
    """points: [(label, value, kind)] kind in list|first|walk|comp|avm; bands: [(lo, hi, cls)]"""
    vals = [v for _, v, _ in points if v] + [x for b in bands for x in b[:2] if x]
    if not vals: return ""
    lo, hi = min(vals) * 0.97, max(vals) * 1.03; pl, pr = 10, 10
    X = lambda v: pl + (w - pl - pr) * (v - lo) / (hi - lo)
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="none" style="width:100%%;height:auto;aspect-ratio:%d/%d">' % (w, h, w, h)]
    for blo, bhi, cls in bands:
        if blo and bhi: out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="3" class="band-%s"/>' % (X(blo), 44 if cls == "range" else 50, max(2, X(bhi) - X(blo)), 24 if cls == "range" else 12, cls))
    out.append('<line x1="%d" x2="%d" y1="62" y2="62" class="grid"/>' % (pl, w - pr))
    step = 100000 if hi - lo < 900000 else 250000
    v = (int(lo // step) + 1) * step
    while v < hi:
        out.append('<line x1="%.1f" x2="%.1f" y1="58" y2="66" class="grid"/><text x="%.1f" y="80" class="tick" text-anchor="middle">%s</text>' % (X(v), X(v), X(v), _nice(v))); v += step
    comp_i = 0
    for lab, v, kind in points:
        if not v: continue
        x = X(v)
        if kind == "comp":
            y = (30, 16, 2)[comp_i % 3] + 8; comp_i += 1
            out.append('<circle cx="%.1f" cy="%d" r="8" fill="var(--card)" stroke="var(--muted)" stroke-width="1.5"/><text x="%.1f" y="%d" class="tick" text-anchor="middle" font-weight="700">%s</text><title>%s</title>' % (x, y, x, y + 4, esc(lab), money(v)))
        elif kind == "list":
            out.append('<line x1="%.1f" x2="%.1f" y1="38" y2="70" stroke="var(--bad)" stroke-width="3"/><text x="%.1f" y="100" class="lab" text-anchor="middle" fill="var(--bad)">%s %s</text>' % (x, x, x, esc(lab), money(v)))
        elif kind in ("first", "walk"):
            out.append('<line x1="%.1f" x2="%.1f" y1="40" y2="70" stroke="var(--brand)" stroke-width="2" stroke-dasharray="4 3"/><text x="%.1f" y="%d" class="tick" text-anchor="%s">%s %s</text>' % (x, x, x + (-4 if kind == "first" else 4), 112, "end" if kind == "first" else "start", esc(lab), money(v)))
    out.append('</svg>')
    return "".join(out)
def svg_map(items, w=720, h=360):
    pts = [c for c in items if c.get("lon") and c.get("lat")]
    if not pts: return ""
    import math as _m
    lon0 = sum(num(c["lon"]) for c in pts) / len(pts) if not hasattr(svg_map, "subj") else svg_map.subj[0]
    lat0 = sum(num(c["lat"]) for c in pts) / len(pts) if not hasattr(svg_map, "subj") else svg_map.subj[1]
    K = 111320 * _m.cos(_m.radians(lat0))
    xy = [((num(c["lon"]) - lon0) * K, (num(c["lat"]) - lat0) * 111320) for c in pts]
    R = max(1600, max(max(abs(x), abs(y)) for x, y in xy) * 1.1)
    cx, cy = w / 2, h / 2; sc = min(w, h) / 2 / R * 0.95
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="xMidYMid meet" style="width:100%%;height:auto;aspect-ratio:%d/%d">' % (w, h, w, h)]
    for r in (500, 1000, 1500):
        if r * sc < min(w, h) / 2:
            out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" class="grid" stroke-dasharray="3 3"/><text x="%.1f" y="%.1f" class="tick">%d m</text>' % (cx, cy, r * sc, cx + r * sc * 0.72, cy - r * sc * 0.72, r))
    out.append('<text x="%.1f" y="14" class="tick" text-anchor="middle">N ↑</text>' % cx)
    col = VCOL
    for (x, y), c in zip(xy, pts):
        px, py = cx + x * sc, cy - y * sc; v = verdict_of(c)
        out.append('<circle cx="%.1f" cy="%.1f" r="10" fill="%s" fill-opacity=".9" stroke="var(--card)" stroke-width="2"><title>%s · %s</title></circle><text x="%.1f" y="%.1f" font-size="11" font-weight="700" text-anchor="middle" fill="#fff">%s</text>' % (px, py, col[v], esc(str(c.get("address", "")).title()), money(c.get("price")), px, py + 4, c.get("_letter", "")))
    out.append('<text x="%.1f" y="%.1f" font-size="24" text-anchor="middle" fill="var(--bad)">★</text>' % (cx, cy + 9))
    out.append('</svg>')
    return "".join(out)
def svg_street_scatter(rows, subj, w=720, h=240):
    import datetime as _dt
    def pdate(sv):
        for f in ("%d %B %Y", "%Y-%m-%d", "%Y-%m"):
            try: return _dt.datetime.strptime(str(sv).strip(), f)
            except Exception: pass
        return None
    pts = [(pdate(r.get("date")), num(r.get("price")), num((r.get("floor_m2") or r.get("land")) if UNIT else r.get("land")), r.get("addr", "")) for r in rows if r.get("price")]
    pts = [p for p in pts if p[0]]
    if len(pts) < 3: return ""
    t0 = min(p[0] for p in pts); t1 = _dt.datetime.today()
    pl, pr, pt, pb = 60, 14, 16, 30
    y0, y1 = min(p[1] for p in pts) * 0.9, max(p[1] for p in pts) * 1.06
    X = lambda d: pl + (w - pl - pr) * ((d - t0).days / max(1, (t1 - t0).days)); Y = lambda v: pt + (h - pt - pb) * (1 - (v - y0) / (y1 - y0))
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="none" style="width:100%%;height:auto;aspect-ratio:%d/%d">' % (w, h, w, h)]
    for k in range(4):
        v = y0 + (y1 - y0) * k / 3
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (pl, w - pr, Y(v), Y(v), pl - 6, Y(v) + 4, _nice(v)))
    _m = _dt.datetime(t0.year, t0.month, 1); _step = 1 if (t1 - t0).days < 400 else (3 if (t1 - t0).days < 1100 else 12)
    while _m <= t1:
        if _m >= t0: out.append('<text x="%.1f" y="%d" class="tick" text-anchor="middle">%s</text>' % (X(_m), h - 8, _m.strftime("%Y-%m") if _step < 12 else _m.strftime("%Y")))
        _mo = _m.month + _step; _m = _dt.datetime(_m.year + (_mo - 1) // 12, (_mo - 1) % 12 + 1, 1)
    lmax = max(p[2] for p in pts) or 1
    for d, v, land, addr in pts:
        r = 5 + 9 * (land / lmax) ** 0.5
        out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="var(--c1)" fill-opacity=".55" stroke="var(--card)" stroke-width="1.5"><title>%s · %s · %s m²</title></circle>' % (X(d), Y(v), r, esc(addr), money(v), "%g" % land))
    if subj.get("list_price"):
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--bad)" stroke-width="2" stroke-dasharray="5 3"/><text x="%d" y="%.1f" class="lab" text-anchor="end" fill="var(--bad)">%s</text>' % (pl, w - pr, Y(num(subj["list_price"])), Y(num(subj["list_price"])), w - pr, Y(num(subj["list_price"])) - 5, money(subj["list_price"])))
    out.append('</svg>')
    return "".join(out)
def svg_timeline_strip(tl, w=720, h=70):
    import datetime as _dt
    def pdate(sv):
        sv = str(sv).strip()
        for f, n in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
            try: return _dt.datetime.strptime(sv[:n], f)
            except Exception: pass
        return None
    pts = [(pdate(r.get("date")), r) for r in tl]; pts = [p for p in pts if p[0]]
    if len(pts) < 2: return ""
    t0 = pts[0][0]; t1 = max(p[0] for p in pts); span = max(1, (t1 - t0).days)
    pl, pr = 30, 30
    X = lambda d: pl + (w - pl - pr) * ((d - t0).days / span)
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="none" style="width:100%%;height:auto;aspect-ratio:%d/%d"><line x1="%d" x2="%d" y1="34" y2="34" class="grid"/>' % (w, h, w, h, pl, w - pr)]
    for i, (d, r) in enumerate(pts):
        last = i == len(pts) - 1; q = "?" in str(r.get("event", "")) or "待" in str(r.get("event", ""))
        out.append('<circle cx="%.1f" cy="34" r="7" fill="%s" stroke="var(--card)" stroke-width="2"/>' % (X(d), "var(--bad)" if last else ("var(--warn)" if q else "var(--brand)")))
        if q: out.append('<text x="%.1f" y="38" font-size="10" font-weight="700" text-anchor="middle" fill="#fff">?</text>' % X(d))
        out.append('<text x="%.1f" y="%d" class="tick" text-anchor="%s">%s</text>' % (X(d), 16 if i % 2 == 0 else 58, "start" if i == 0 else ("end" if last else "middle"), esc(str(r.get("date"))[:7])))
    out.append('</svg>')
    return "".join(out)
def svg_scatter(items, subj, rng, w=720, h=260):
    xk = "floor_m2" if UNIT else "land_m2"   # x axis: floor area for units, land area for houses
    pts = [c for c in items if c.get(xk) and c.get("price")]
    if not pts: return ""
    xs = [num(c[xk]) for c in pts] + ([num(subj.get(xk))] if subj.get(xk) else [])
    ys = [num(c["price"]) for c in pts] + ([num(subj.get("list_price"))] if subj.get("list_price") else [])
    x0, x1 = min(xs) * 0.92, max(xs) * 1.06; y0, y1 = min(ys) * 0.92, max(ys) * 1.06
    pl, pr, pt, pb = 60, 14, 16, 30
    X = lambda v: pl + (w - pl - pr) * (v - x0) / (x1 - x0); Y = lambda v: pt + (h - pt - pb) * (1 - (v - y0) / (y1 - y0))
    out = ['<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="none" style="width:100%%;height:auto;aspect-ratio:%d/%d">' % (w, h, w, h)]
    for k in range(4):
        v = y0 + (y1 - y0) * k / 3
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (pl, w - pr, Y(v), Y(v), pl - 6, Y(v) + 4, _nice(v)))
    for k in range(5):
        v = x0 + (x1 - x0) * k / 4
        out.append('<text x="%.1f" y="%d" class="tick" text-anchor="%s">%.0f m²</text>' % (X(v), h - 8, "start" if k == 0 else ("end" if k == 4 else "middle"), v))
    if rng and rng[0] and rng[1]:
        out.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="var(--ok)" opacity=".13"/>' % (pl, Y(float(rng[1])), w - pl - pr, max(1, Y(float(rng[0])) - Y(float(rng[1])))))
    col = VCOL
    for c in pts:
        v = verdict_of(c); be = c.get("bookend") if v != "未知" else None
        out.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="%s" fill-opacity=".9" stroke="%s" stroke-width="%d"><title>%s · %s · %s m²</title></circle><text x="%.1f" y="%.1f" font-size="10" font-weight="700" text-anchor="middle" fill="#fff" pointer-events="none">%s</text>' % (
            X(num(c[xk])), Y(num(c["price"])), 9, col[v], "var(--ink-strong)" if be else "var(--card)", 3 if be else 2,
            esc(str(c.get("address", "")).title()), money(c.get("price")), c.get(xk), X(num(c[xk])), Y(num(c["price"])) + 3.5, c.get("_letter", "")))
    if subj.get(xk) and subj.get("list_price"):
        sx, sy = X(num(subj[xk])), Y(num(subj["list_price"]))
        out.append('<text x="%.1f" y="%.1f" font-size="22" text-anchor="middle" fill="var(--bad)">★</text><text x="%.1f" y="%.1f" class="lab" text-anchor="middle">%s</text>' % (sx, sy + 8, sx, sy - 14, money(subj["list_price"])))
    out.append('</svg>')
    return "".join(out)
def tbl_src(inner):
    return '<details class="src-tbl"><summary>%s</summary>%s</details>' % (t("chart_src"), inner)

# ---------------------------------------------------------------- comparables scoring
SCORE_KEYS = ("land", "slope", "condition")
def score_val(v):
    if v in (1, "+1", "+", "better", "优"): return 1
    if v in (-1, "-1", "-", "worse", "逊"): return -1
    if v in (0, "0", "same", "同", "=", "相当"): return 0
    return None
def completeness(c):
    if UNIT:   # 8 unit fields: floor area, cars, level, aspect, built, renovation, levies, date & price
        fields = [c.get("floor_m2"), c.get("cars"), c.get("level"), c.get("orientation") or c.get("aspect"), c.get("built"),
                  c.get("reno"), c.get("levies"), (c.get("date") and c.get("price"))]
    else:
        fields = [c.get("land_m2"), c.get("landslip") or c.get("slope"), c.get("street_side"), c.get("built"),
                  c.get("floor_m2"), c.get("wall"), c.get("reno"), (c.get("date") and c.get("price"))]
    return sum(1 for f in fields if f not in (None, "", "—", "unknown", "未知", 0, False))
def bk_min(): return 4 if UNIT else 5   # minimum completeness for a bookend
def verdict_of(c):
    v = c.get("verdict")
    if v in ("优于", "相当", "逊于", "未知", "Superior", "Close", "Inferior", "Unknown"):
        return {"Superior": "优于", "Close": "相当", "Inferior": "逊于", "Unknown": "未知"}.get(v, v)
    sc = [score_val(c.get("scores", {}).get(k)) for k in SCORE_KEYS]
    known = [s for s in sc if s is not None]
    if not known: return "未知"
    s = sum(known)
    return "优于" if s > 0 else ("逊于" if s < 0 else "相当")
VCOL = {"优于": "var(--bad)", "相当": "var(--accent)", "逊于": "var(--ok)", "未知": "var(--na)"}
VCLS = {"优于": "sup", "相当": "close", "逊于": "inf", "未知": "unk"}
def vlabel(v): return {"优于": t("v_sup"), "相当": t("v_close"), "逊于": t("v_inf"), "未知": t("v_unk")}[v]
def sc_label(v):
    s = score_val(v)
    return {1: t("sc_better"), 0: t("sc_same"), -1: t("sc_worse"), None: t("sc_unknown")}[s]

def comp_card(c, subj, warnings):
    v = verdict_of(c); cls = VCLS[v]
    comp = completeness(c); be = c.get("bookend")
    if v == "未知" and be in ("upper", "lower"):   # an unscored card is never a bookend
        warnings.append("bookend %s has all three scores unknown and was not used as a bookend: %s" % (be, c.get("address")))
        be = None; unk_be = True
    else:
        unk_be = False
    open_ = v == "相当" or be in ("upper", "lower")
    if be in ("upper", "lower") and comp < bk_min():
        warnings.append("bookend %s has completeness %d/8 (<%d): %s" % (be, comp, bk_min(), c.get("address")))
    tags = ('<span class="tag letter">%s</span>' % c.get("_letter", "")) + '<span class="tag">%s</span>' % vlabel(v)
    if be == "upper": tags += '<span class="tag be">%s</span>' % t("bk_upper")
    if be == "lower": tags += '<span class="tag be">%s</span>' % t("bk_lower")
    sdots = "".join('<i class="sd %s" title="%s"></i>' % ({1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get(k))], k) for k in SCORE_KEYS)
    cdots = "".join('<i class="cd%s"></i>' % (" on" if i < comp else "") for i in range(8))
    head = '%s<b>%s</b> · %s · <b>%s</b><span class="sdots">%s</span><span class="cmp">%s %d/8 <span class="cdots">%s</span></span><span class="dist">%s</span>' % (
        tags, esc(str(c.get("address", "")).title()), esc(c.get("date", "")), money(c.get("price")), sdots,
        t("completeness"), comp, cdots, (str(c.get("dist_m")) + " m") if c.get("dist_m") is not None else "")
    land_cmp = ""
    if c.get("land_m2") and subj.get("land_m2"):
        land_cmp = "%+.0f m²" % (num(c["land_m2"]) - num(subj["land_m2"]))
    sc = c.get("scores", {})
    basics = "%s / %s / %s m² / %s / %s" % (
        (str(c.get("beds")) + ("卧" if LANG == "zh" else "bd")) if c.get("beds") else "—",
        (str(c.get("baths")) + ("卫" if LANG == "zh" else "ba")) if c.get("baths") else "—",
        c.get("floor_m2") or "—", c.get("built") or "—", c.get("storeys") or "—")
    mat = c.get("wall") or t("unknown"); reno = c.get("reno") or t("unknown")
    vtail = ("<br><span class=\"warn\">" + t("bk_low_warn") + "</span>") if (be and comp < bk_min()) else ""
    if unk_be: vtail += "<br><span class=\"warn\">" + t("bk_unk_warn") + "</span>"
    if UNIT:
        fl_cmp = ("%+.0f m²" % (num(c["floor_m2"]) - num(subj["floor_m2"]))) if c.get("floor_m2") and subj.get("floor_m2") else ""
        ub = "%s / %s / %s m² / %s" % (
            (str(c.get("beds")) + ("卧" if LANG == "zh" else "bd")) if c.get("beds") else "—",
            (str(c.get("baths")) + ("卫" if LANG == "zh" else "ba")) if c.get("baths") else "—",
            c.get("floor_m2") or "—", c.get("built") or "—")
        ub2 = " · ".join("%s %s" % (t(lab), esc(val) if val not in (None, "") else "—") for lab, val in (
            ("u_level", c.get("level")), ("u_cars", c.get("cars")), ("u_aspect", c.get("orientation") or c.get("aspect")), ("u_levies", c.get("levies"))))
        lvl = " · ".join(str(x) for x in (c.get("level"), c.get("orientation") or c.get("aspect"), c.get("view")) if x not in (None, ""))
        body = '''<div class="cg"><div><h5>%s</h5>%s<br>%s</div>
<div><h5>%s</h5>%s %s</div>
<div><h5>%s</h5>%s %s(%s) · %s %s(%s) · %s %s(%s;%s)<br>%s</div>
<div><h5>%s</h5><b>%s</b>%s</div></div>''' % (
            t("cg_basic"), esc(ub), ub2,
            t("cg_price"), t("u_pm2"), money(num(c.get("price")) / num(c.get("floor_m2"))) if c.get("floor_m2") and c.get("price") else "—",
            t("cg_cmp"), t("sc_land"), sc_label(sc.get("land")), esc(" ".join(x for x in (fl_cmp, ("%s %s" % (t("u_cars"), c.get("cars"))) if c.get("cars") not in (None, "") else "") if x) or "—"),
            t("sc_slope"), sc_label(sc.get("slope")), esc(lvl or "—"),
            t("sc_cond"), sc_label(sc.get("condition")), esc(c.get("built") or "—"), esc(reno),
            esc(c.get("note", "")),
            t("cg_verdict"), vlabel(v), vtail)
        return '<details class="comp %s" id="comp-%s"%s><summary>%s</summary>%s</details>' % (cls, c.get("_letter", ""), " open" if open_ else "", head, body)
    body = '''<div class="cg"><div><h5>%s</h5>%s<br>%s %s m² · LV %s</div>
<div><h5>%s</h5>P/LV <b>%s</b> · LV %s/m² · %s/m²</div>
<div><h5>%s</h5>%s %s(%s) · %s %s(%s) · %s %s(%s;%s / %s)<br>%s</div>
<div><h5>%s</h5><b>%s</b>%s</div></div>''' % (
        t("cg_basic"), basics, ("土地" if LANG == "zh" else "Land"), c.get("land_m2") or "—", money(c.get("lv")) if c.get("lv") else "—",
        t("cg_price"), c.get("p_lv") or "—", money(c.get("lv_m2")) if c.get("lv_m2") else "—",
        money(num(c.get("price")) / num(c.get("land_m2"))) if c.get("land_m2") and c.get("price") else "—",
        t("cg_cmp"), t("sc_land"), sc_label(sc.get("land")), esc(land_cmp or "—"),
        t("sc_slope"), sc_label(sc.get("slope")), esc(c.get("landslip") or c.get("slope") or "—"),
        t("sc_cond"), sc_label(sc.get("condition")), esc(c.get("built") or "—"), esc(mat), esc(reno),
        esc(c.get("note", "")),
        t("cg_verdict"), vlabel(v), vtail)
    return '<details class="comp %s" id="comp-%s"%s><summary>%s</summary>%s</details>' % (cls, c.get("_letter", ""), " open" if open_ else "", head, body)

# ---------------------------------------------------------------- sections
OPEN_BY_DEFAULT = {"s1"}   # two-layer length: summary + overview open; the rest are collapsible appendices
def sec(key, inner, hint=""):
    return '<details class="sec" id="%s"%s><summary><h2>%s</h2><span class="hint">%s</span></summary>%s</details>' % (key, " open" if key in OPEN_BY_DEFAULT else "", t(key), esc(hint), inner)

def build(d):
    global LANG, UNIT
    meta = d.get("meta", {}); LANG = meta.get("lang", LANG); UNIT = is_unit(d)
    subj = d.get("subject", {}); summ = d.get("summary", {}); warnings = []
    # status cards: summary.cards (preferred) > status_cards (older files) > the five default labels for this mode
    data_cards = summ.get("cards") or d.get("status_cards") or []
    scards = data_cards or [{"label": lab[0 if LANG == "zh" else 1], "status": "na", "value": "—"} for lab in DEFAULT_CARDS["unit" if UNIT else "house"]]
    date = meta.get("date") or datetime.date.today().isoformat()
    title = meta.get("title") or ("%s 尽调(公开数据版)" % subj.get("address", "") if LANG == "zh" else "%s due diligence (public-data edition)" % subj.get("address", ""))
    # banner
    btn = ""
    if meta.get("session_resume_url"):
        btn += '<a href="%s">%s</a>' % (esc(meta["session_resume_url"]), t("back"))
    btn += '<button onclick="navigator.clipboard.writeText(%s)">%s</button>' % (json.dumps(title, ensure_ascii=False), t("copy_title"))
    banner = '<header class="banner"><div class="wrap-in"><h1>%s</h1><div class="sub">%s · %s · %s</div><div class="btns">%s</div></div></header>' % (
        esc(title), date, esc(subj.get("address", "")), esc(meta.get("one_liner", "")), btn)
    lo0, hi0 = (summ.get("range") or [None, None])[:2]
    short = re.split(r",\s*", subj.get("address", ""))[0]
    cards0 = scards
    flood = cards0[0] if cards0 else {}
    navlinks = "".join('<a href="#%s">%s</a>' % (k, re.split(r"[:: ]", re.sub(r"^\d+\.\s*", "", t(k)))[0]) for k in ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9"])
    banner += '<nav class="sticky"><b>%s</b><span>%s %s</span><span>%s %s–%s</span><span class="%s">%s:%s</span><span class="links">%s</span></nav>' % (
        esc(short), t("nav_list"), money(subj.get("list_price")), t("nav_range"), money(lo0), money(hi0),
        cls_of(flood.get("status")), esc(flood.get("label", "")), esc(flood.get("value", "")), navlinks)

    # ---- summary (first screen)
    lo, hi = (summ.get("range") or [None, None])[:2]
    offer = summ.get("offer", {})
    offer_html = ""
    if offer:
        offer_html = '<div class="offer"><div><div class="k">%s</div><div class="n">%s</div></div><div><div class="k">%s</div><div class="n">%s</div></div><div><div class="k">%s</div><div class="n">%s</div><div class="note">%s</div></div></div>' % (
            t("offer_first"), money(offer.get("first")), t("offer_walk"), money(offer.get("walk_away")),
            t("offer_conf"), esc(offer.get("confidence", "—")), esc(offer.get("confidence_note", "")))
    # hero: photos (hot-linked, credited) + facts panel
    ph0 = d.get("photos", {}); imgs = ph0.get("images") or []
    edition = (meta.get("edition") or "public").lower()
    listing_url = next((sr.get("url") for sr in ph0.get("sources", []) if sr.get("url")), "")
    if imgs:
        gal = '<div class="car"><img id="carMain" class="main" src="%s" alt="%s" referrerpolicy="no-referrer" loading="eager"><button class="cb l" type="button" onclick="car(-1)" aria-label="prev">‹</button><button class="cb r" type="button" onclick="car(1)" aria-label="next">›</button><div id="carCap" class="cap">%s</div></div>' % (
            esc(imgs[0].get("url")), esc(imgs[0].get("caption", "")), esc("1 / %d · %s" % (len(imgs), imgs[0].get("caption", ""))))
        gal += '<div class="thumbs" id="carThumbs">%s</div>' % "".join('<img src="%s" alt="" referrerpolicy="no-referrer" loading="lazy" class="%s" onclick="car(null,%d)">' % (esc(i.get("url")), "on" if n == 0 else "", n) for n, i in enumerate(imgs))
        gal += '<p class="src">%s%s</p>' % (('<a href="%s" target="_blank" rel="noopener">%s</a> · ' % (esc(listing_url), t("gallery_link"))) if listing_url else "", t("photo_credit", src=esc(ph0.get("credit_source") or ph0.get("sources", [{}])[0].get("name", ""))))
        gal += '<script>var CAR=%s,CI=0;function car(d,i){CI=(i!=null?i:CI+d+CAR.length)%%CAR.length;var m=document.getElementById("carMain");m.src=CAR[CI].url;document.getElementById("carCap").textContent=(CI+1)+" / "+CAR.length+" · "+(CAR[CI].caption||"");document.querySelectorAll("#carThumbs img").forEach(function(x,n){x.classList.toggle("on",n==CI)})}</script>' % json.dumps([{"url": i.get("url"), "caption": i.get("caption", "")} for i in imgs], ensure_ascii=False)
    else:
        gal = '<div class="car empty"><div>%s</div>%s%s</div>' % (t("photo_placeholder"),
            ('<a href="%s">%s</a>' % (esc(ph0["streetview_url"]), t("streetview"))) if ph0.get("streetview_url") else "", nextcell(t("photo_next")))
    ba = ph0.get("before_after") or []
    if ba and edition == "internal":
        gal += '<h5 style="margin-top:12px">%s</h5><div class="ba">%s</div>' % (t("ba_h"), "".join('<figure><div class="pair"><img src="%s" alt="before" referrerpolicy="no-referrer" loading="lazy"><img src="%s" alt="after" referrerpolicy="no-referrer" loading="lazy"></div><figcaption>%s</figcaption></figure>' % (esc(x.get("before")), esc(x.get("after")), esc(x.get("caption", ""))) for x in ba))
    facts = ""
    for key, lab in (("beds", "f_beds"), ("baths", "f_baths"), ("cars", "f_cars"), ("land_m2", "f_land"), ("floor_m2", "f_floor"), ("built", "f_built")):
        v = subj.get(key)
        if UNIT and key == "land_m2" and subj.get("strata_m2") not in (None, ""): v = subj["strata_m2"]   # unit: strata lot area, never "land"
        if v not in (None, ""):
            v = ("%g" % float(v)) if key in ("land_m2", "floor_m2") and str(v).replace(".", "").isdigit() else v
            facts += "<span><b>%s</b> %s</span>" % (esc(v), t(lab))
    lo, hi = (summ.get("range") or [None, None])[:2]
    offer = summ.get("offer", {})
    dom0 = d.get("dom", {}); domtxt = ""
    if dom0.get("months_approx") is not None:
        domtxt = t("k_dom_txt", basis=esc(dom0.get("basis", "")), m=dom0["months_approx"])
        if dom0.get("suburb_median_dom"): domtxt += t("k_dom_sub", d=dom0["suburb_median_dom"])
    lv0 = subj.get("land_value") or {}
    kv2 = '<dt>%s</dt><dd><span class="big">%s</span></dd>' % (t("k_list"), money(subj.get("list_price")))
    kv2 += '<dt>%s</dt><dd><b class="mid">%s – %s</b></dd>' % (t("k_range"), money(lo), money(hi))
    if offer.get("walk_away"): kv2 += '<dt>%s</dt><dd><b>%s</b></dd>' % (t("k_walk"), money(offer.get("walk_away")))
    if subj.get("status_line"): kv2 += '<dt>%s</dt><dd class="%s">%s</dd>' % (t("k_status"), cls_of(subj.get("status_class", "warn")), esc(subj["status_line"]))
    if domtxt: kv2 += '<dt>%s</dt><dd>%s</dd>' % (t("k_dom"), domtxt)
    if lv0.get("latest"):
        if UNIT: kv2 += '<dt>%s</dt><dd>%s</dd>' % (t("k_lv"), t("k_lv_val", v=money(lv0["latest"])))
        else: kv2 += '<dt>%s</dt><dd>%s(%s)</dd>' % (t("k_lv"), money(lv0["latest"]), esc(str(lv0.get("date", ""))[:4]))
    addr_parts = re.split(r",\s*", subj.get("address", ""), maxsplit=1)
    panel = '<div class="addr">%s</div><div class="src">%s</div><div class="facts">%s</div><dl class="kv2">%s</dl>' % (
        esc(addr_parts[0]), esc(" · ".join(x for x in [addr_parts[1] if len(addr_parts) > 1 else "", subj.get("lot_dp", ""), subj.get("dwelling", "")] if x)), facts, kv2)
    hero = '<section class="hero"><div class="gallery">%s</div><div class="panel">%s</div></section>' % (gal, panel)
    cards = ""
    for c in scards:
        cards += '<div class="card"><div class="k">%s</div><div class="v %s">%s</div><div class="note">%s</div>%s</div>' % (
            esc(c.get("label")), cls_of(c.get("status")), esc(c.get("value")), esc(c.get("note", "")), nextcell(c.get("next", "")))
    offer_html = ""
    if offer:
        offer_html = '<div class="offer"><div><div class="k">%s</div><div class="n">%s</div></div><div><div class="k">%s</div><div class="n">%s</div></div><div><div class="k">%s</div><div class="n">%s</div><div class="note">%s</div></div></div>' % (
            t("offer_first"), money(offer.get("first")), t("offer_walk"), money(offer.get("walk_away")),
            t("offer_conf"), esc(offer.get("confidence", "—")), esc(offer.get("confidence_note", "")))
    summary = '%s<div class="verdict"><b>%s:</b>%s</div><div class="cards">%s</div>%s<p class="maxrisk"><b>%s:</b>%s</p><p class="note disclaimer">%s</p>' % (
        hero, t("one_line"), esc(summ.get("verdict_line", "")), cards, offer_html, t("max_risk"), esc(summ.get("max_risk", "")), t("disclaimer", date=date))

    S = []
    # ---- 1 overview
    kv = ""
    for k, v in subj.get("facts", []):
        kv += "<div><b>%s</b>%s</div>" % (esc(k), esc(v))
    ph = d.get("photos", {}); phtml = ""
    if ph.get("sources"):
        phtml += "<ul>" + "".join('<li><a href="%s">%s</a> — %s</li>' % (esc(s.get("url")), esc(s.get("name")), esc(s.get("crosscheck", ""))) for s in ph["sources"]) + "</ul>"
        if ph.get("material_from_photos"):
            _mfp = str(ph["material_from_photos"]); _pre = _mfp.lstrip().lower().startswith((T["material_from_photo"][0], T["material_from_photo"][1].lower()))
            phtml += ("<p>%s</p>" % esc(_mfp)) if _pre else ("<p><b>%s:</b>%s</p>" % (t("material_from_photo"), esc(_mfp)))
    else:
        phtml += '<div class="paid">%s%s</div>' % (t("photo_none"), nextcell(t("photo_next")))
    if ph.get("streetview_url"):
        phtml += '<p class="note"><a href="%s">%s</a></p>' % (esc(ph["streetview_url"]), t("streetview"))
    S.append(sec("s1", '<div class="two"><div><div class="kv">%s</div></div><div><h3 style="margin-top:0">%s</h3>%s</div></div>' % (kv, t("photos"), phtml)))

    # ---- 2 timeline + ruler
    tl = d.get("timeline", [])
    tlh = '<h3 style="margin-top:0">%s</h3>%s<p class="note">%s</p><ol class="tl">%s</ol>' % (t("tl_h"), svg_timeline_strip(tl), t("tl_strip_note") if svg_timeline_strip(tl) else "",
          "".join('<li><span class="d">%s</span><div><div class="e">%s</div><div class="src">%s</div></div></li>' % (esc(r.get("date")), esc(r.get("event")), esc(r.get("source"))) for r in tl))
    dom = d.get("dom", {}); domh = "<h3>%s</h3>" % t("dom_h")
    if dom.get("months_approx") is not None:
        domh += "<p>%s</p>" % t("dom_approx", m=dom["months_approx"], basis=esc(dom.get("basis", "")))
    if dom.get("suburb_median_dom"):
        domh += "<p>%s</p>" % t("dom_suburb", d=dom["suburb_median_dom"], src=esc(dom.get("suburb_dom_source", "")))
    if dom.get("months_approx") is not None and dom.get("suburb_median_dom"):
        domh += "<h3>%s</h3>%s" % (t("dom_bars_h"), svg_hbars([(t("dom_this"), round(float(dom["months_approx"]) * 30.4), ""), (t("dom_sub"), float(dom["suburb_median_dom"]), "")], fmt=lambda v: "%.0f d" % v))
    if dom.get("price_history_text"):
        domh += "<p>%s</p>" % esc(dom["price_history_text"])
    if dom.get("price_history_status", "unverified") != "verified":
        domh += '<p><span class="warn">%s</span></p>%s' % (t("dom_unverified"), paid("price-history", t("dom_h")))
    # price narrative: one axis
    _of = summ.get("offer", {}); _rng = summ.get("range") or [None, None]; _avm = summ.get("avm_range") or []
    _pts = [(t("nav_list"), subj.get("list_price"), "list"), (t("offer_first"), _of.get("first"), "first"), (t("offer_walk"), _of.get("walk_away"), "walk")]
    for _i, _c in enumerate(d.get("comps", {}).get("items", [])):
        if _c.get("price"): _pts.append((letter(_i), num(_c["price"]), "comp"))
    _bands = [(_rng[0], _rng[1], "range")] + ([(_avm[0], _avm[-1], "avm")] if len(_avm) >= 2 else [])
    pline = svg_priceline(_pts, _bands)
    tth = tt("tier_th")
    tiers = '<h3>%s</h3><table class="tiers"><tr>%s</tr><tr><td>%s</td><td><b>%s</b></td><td>%s</td></tr><tr><td>%s</td><td><b>%s – %s</b></td><td>%s</td></tr><tr><td>%s</td><td><b>%s</b></td><td>%s</td></tr></table>' % (
        t("tiers_h"), "".join("<th>%s</th>" % x for x in tth),
        t("tier_first"), money(_of.get("first")), esc(d.get("pricing", {}).get("lower", "")),
        t("tier_fair"), money(_rng[0]), money(_rng[1]), esc(summ.get("range_note", ""))[:220] + ("…" if len(summ.get("range_note", "")) > 220 else ""),
        t("tier_walk"), money(_of.get("walk_away")), esc(_of.get("confidence_note", "")))
    pnh = ("<h3>%s</h3>%s<p class=\"note\">%s</p>%s" % (t("priceline_h"), pline, t("priceline_note"), tiers)) if pline else ""
    rl = d.get("ruler", {}); rh = pnh
    if rl.get("prices"):
        prices = sorted(float(p) for p in rl["prices"]); L = float(rl.get("list") or subj.get("list_price") or 0)
        mn = float(rl.get("min") or min(prices) * 0.95)
        p95 = prices[min(len(prices) - 1, int(len(prices) * 0.95))]
        cap = max(L * 1.6, p95 * 1.05, float((summ.get("range") or [0, 0])[1] or 0) * 1.15)
        mx = min(float(rl.get("max") or max(prices) * 1.05), cap)
        x = lambda p: max(0, min(100, (p - mn) / (mx - mn) * 100))
        pct = sum(1 for p in prices if p < L) / len(prices) * 100 if prices else 0
        binw = 25000 if (mx - mn) < 2500000 else 50000
        bins = {}
        for p in prices:
            if p > mx: continue
            b = int((p - mn) // binw); bins[b] = bins.get(b, 0) + 1
        dots = "".join('<div class="dot" style="left:%.1f%%;top:%dpx"></div>' % (x(mn + (b + 0.5) * binw), 46 - 7 * min(k, 5)) for b, c in bins.items() for k in range(c))
        dots += "".join('<div class="cl" style="left:%.1f%%;top:%dpx" title="%s %s">%s</div>' % (x(num(c["price"])), 4 + 14 * (i % 2), esc(str(c.get("address", "")).title()), money(c.get("price")), letter(i)) for i, c in enumerate(d.get("comps", {}).get("items", [])) if c.get("price") and mn <= num(c["price"]) <= mx)
        over = sum(1 for p in prices if p > mx)
        more = ('<div class="lab more">%s</div>' % t("ruler_more", cap=money(mx), n=over)) if over else ""
        step = 500000 if mx - mn > 2000000 else 250000
        _axis = [mn + i * step for i in range(int((mx - mn) / step) + 1)]
        labs = "".join('<div class="lab axis" style="left:%.1f%%;%s">$%.2fM</div>' % (x(p), "transform:none" if i == 0 else ("transform:translateX(-100%)" if i == len(_axis) - 1 else ""), p / 1e6) for i, p in enumerate(_axis))
        of = summ.get("offer", {})
        _ticks = [(lab, v) for lab, v in ((t("offer_first"), of.get("first")), (t("offer_walk"), of.get("walk_away"))) if v]
        ticks = "".join('<div class="tick2" style="left:%.1f%%" title="%s %s"></div>' % (x(float(v)), lab, money(v)) for lab, v in _ticks)
        tick_note = (" " + " / ".join("%s %s" % (lab, money(v)) for lab, v in _ticks) + (" = 虚线。" if LANG == "zh" else " = dashed lines.")) if _ticks else ""
        lo_r, hi_r = (summ.get("range") or [None, None])[:2]
        band = ('<div class="band" style="left:%.1f%%;width:%.1f%%"></div>' % (x(float(lo_r)), max(0.5, x(float(hi_r)) - x(float(lo_r))))) if lo_r and hi_r else ""
        rh += "<h3>%s</h3><p class=\"note\">%s</p><p>%s</p><div class=\"ruler\">%s%s<div class=\"me\" style=\"left:%.1f%%\"></div><div class=\"lab\" style=\"left:%.1f%%;top:2px;color:#b42318;font-weight:700\">%s</div>%s</div><p class=\"note\">%s</p>" % (
            t("range_how"), esc(summ.get("range_note", "")),
            t("ruler_lead", window=esc(rl.get("window_label", "")), n=rl.get("n", len(prices)), median=money(rl.get("median") or statistics.median(prices)), list=money(L)),
            band, dots + ticks + more, x(L), x(L), t("ruler_me", list=money(L), pct=pct), labs, t("ruler_note2") + tick_note)
    S.append(sec("s2", tlh + domh + rh))

    # ---- 3 hazards
    hz = d.get("hazards", []); rows = ""; manual = []
    for h in hz:
        tier = h.get("tier", "covered"); st = h.get("status", "ok")
        res = h.get("result") or (t("not_detected") if (tier == "covered" and st == "ok") else (t("uncovered") if tier == "uncovered" else (t("paid_short") if tier == "paid" else (t("cond") if st == "cond" else t("applies")))))
        nxt = h.get("next", "")
        if st == "cond" and tier != "paid":
            nxt = (t("flood_cond_next") + (" " + nxt if nxt else ""))
        if tier == "paid":
            cell = paid(h.get("slug", "item"), h.get("item"))
        else:
            cell = nextcell(nxt)
        if nxt: manual.append((h.get("item"), nxt))
        rows += '<tr><td>%s</td><td class="%s">%s</td><td>%s</td><td class="dt">%s</td><td>%s</td><td class="nx">%s</td></tr>' % (
            esc(h.get("item")), cls_of(st), esc(res), esc(h.get("source", "")), esc(h.get("date", date)), esc(h.get("note", "")), cell)
    def _tile(h):
        return (
        '<details class="tile %s %s"><summary><span class="dot"></span><b>%s</b><span class="r">%s</span></summary><div class="tb">%s%s%s</div></details>' % (
            cls_of(h.get("status", "ok")) or "ok", "t-" + h.get("tier", "covered"), esc(h.get("item")),
            esc(h.get("result") or (t("not_detected") if (h.get("tier", "covered") == "covered" and h.get("status", "ok") == "ok") else (t("uncovered") if h.get("tier") == "uncovered" else (t("paid_short") if h.get("tier") == "paid" else (t("cond") if h.get("status") == "cond" else t("applies")))))),
            ('<div class="note">%s</div>' % esc(h.get("note"))) if h.get("note") else "",
            nextcell((t("flood_cond_next") + " " + h.get("next", "")) if h.get("status") == "cond" else h.get("next", "")) if h.get("tier") != "paid" else paid(h.get("slug", "item"), h.get("item")),
            ('<div class="src">%s · %s</div>' % (esc(h.get("source", "")), esc(h.get("date", date)))) if h.get("source") else ""))
    _rank = {"bad": 0, "cond": 0, "warn": 1, "ok": 2}
    _main = sorted([h for h in hz if h.get("tier", "covered") == "covered"], key=lambda h: _rank.get(h.get("status", "ok"), 3))
    _grey = [h for h in hz if h.get("tier", "covered") != "covered"]
    _n = {"hit": sum(1 for h in hz if h.get("status") in ("bad", "cond")), "watch": sum(1 for h in hz if h.get("status") == "warn"), "ok": sum(1 for h in hz if h.get("status") == "ok" and h.get("tier", "covered") == "covered"), "none": len(_grey)}
    _tot = max(1, len(hz))
    cov = '<div class="cov"><div class="covbar">%s</div><div class="covleg">%s</div></div>' % (
        "".join('<span class="%s" style="width:%.1f%%"></span>' % (k, 100.0 * v / _tot) for k, v in (("bad", _n["hit"]), ("warn", _n["watch"]), ("ok", _n["ok"]), ("na", _n["none"])) if v),
        " · ".join("<b class=\"%s\">%d</b> %s" % (k, v, lab) for k, v, lab in (("bad", _n["hit"], t("cov_hit")), ("warn", _n["watch"], t("cov_watch")), ("ok", _n["ok"], t("cov_ok")), ("na", _n["none"], t("cov_none")))))
    tiles = '<p class="note">%s</p>%s<div class="tiles">%s</div>' % (t("tiles_lead"), cov, "".join(_tile(h) for h in _main))
    if _grey:
        tiles += '<details class="greygroup"><summary>%s</summary><div class="tiles">%s</div></details>' % (t("tiles_grey", n=len(_grey)), "".join(_tile(h) for h in _grey))
    hz_tbl = "<table class=\"hz\"><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>%s</table>" % (
        t("th_layer"), t("th_result"), t("th_source"), t("th_date"), t("th_note"), t("th_next"), rows)
    S.append(sec("s3", tiles + tbl_src(hz_tbl) + "<p class=\"note\">%s</p>" % t("hazard_rule")))

    # ---- 4 land
    ld = d.get("land", {})
    def read_fig(key):
        p = ld.get(key)
        if not p: return ""
        if p.lstrip().startswith("<svg"): return p
        fp = p if os.path.isabs(p) else os.path.join(os.path.dirname(os.path.abspath(d["_path"])), p)
        return open(fp, encoding="utf-8").read() if os.path.exists(fp) else '<p class="na">[%s missing: %s]</p>' % (key, esc(p))
    lkv = "".join("<div><b>%s</b>%s</div>" % (esc(k), esc(v)) for k, v in ld.get("facts", []))
    lvh = ""
    lvhist = (subj.get("land_value") or {}).get("history") or {}
    if lvhist:
        ys = sorted(lvhist)
        _yrs = sorted(lvhist.keys()); lvh = "<h3>%s</h3>%s%s<p class=\"note\">%s</p>" % (t("lv_h"), svg_bars([num(lvhist[y]) for y in _yrs], [str(y) for y in _yrs], fmt=money, h=180), tbl_src("<table><tr>%s</tr><tr>%s</tr></table>" % ("".join("<th>%s</th>" % esc(y) for y in _yrs), "".join("<td>%s</td>" % money(lvhist[y]) for y in _yrs))), esc(ld.get("lv_note", "")))
    ss = ld.get("street_sales", []); _sc = svg_street_scatter(ss, subj); ssh = ("<h3>%s</h3>%s" % (t("street_scatter_h"), _sc)) if _sc else ""
    if ss:
        ssh += "<h3>%s</h3><table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>%s</table>" % (t("street_sales_h"),
              "Address", "Price", "Date", "m²" if UNIT else "Land", "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s m²</td></tr>" % (esc(r.get("addr")), money(r.get("price")), esc(r.get("date")), esc((r.get("floor_m2") or r.get("land")) if UNIT else r.get("land"))) for r in ss))
    if UNIT:   # neutral captions; fall / gradient text only when the data actually has a gradient
        _pf = ld.get("profile_flat"); _grad = isinstance(_pf, dict) and num(_pf.get("fall")) != 0
        _figa = read_fig("site_svg"); _figa = ('<h3 style="margin-top:0">%s</h3>%s' % (t("fig_a"), _figa)) if _figa else ""
        _figb = ("<p class=\"note\">%s</p>" % t("profile_flat", s=_pf.get("street", "—"), r=_pf.get("rear", "—"), f=_pf.get("fall", 0))) if _grad else read_fig("profile_svg")
        land_html = '<div class="two"><div>%s</div><div><div class="kv" style="grid-template-columns:1fr">%s</div>%s</div></div>%s%s' % (
            _figa, lkv, lvh, ("<h3>%s</h3>%s" % (t("profile_h"), _figb)) if _figb else "", ssh)
    else:
        land_html = '<div class="two"><div>%s</div><div><div class="kv" style="grid-template-columns:1fr">%s</div>%s</div></div><h3>%s</h3>%s%s' % (
        read_fig("site_svg"), lkv, lvh, t("profile_h"), (("<p class=\"note\">%s</p>" % t("profile_flat", s=ld["profile_flat"].get("street", "—"), r=ld["profile_flat"].get("rear", "—"), f=ld["profile_flat"].get("fall", 0))) if isinstance(ld.get("profile_flat"), dict) else read_fig("profile_svg")), ssh)
    S.append(sec("s4", land_html))

    # ---- 5 comps
    for _i, _c in enumerate(d.get("comps", {}).get("items", [])): _c["_letter"] = letter(_i)
    cp = d.get("comps", {}); items = cp.get("items", [])
    csubj = cp.get("subject") or {"land_m2": subj.get("land_m2")}
    if UNIT and not csubj.get("floor_m2"): csubj = dict(csubj, floor_m2=subj.get("floor_m2"))
    cards_html = "".join(comp_card(c, csubj, warnings) for c in items)
    plv = sorted(num(c["p_lv"]) for c in items if c.get("p_lv"))
    svg_map.subj = (subj.get("lon"), subj.get("lat")) if subj.get("lon") and subj.get("lat") else None
    if not svg_map.subj: delattr(svg_map, "subj")
    mth = tt("matrix_th")
    _sd = lambda c, k: {1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get(k))]
    if UNIT:   # floor m² / level (+ level·aspect·view score) / cars (+ area & cars score)
        _rows = "".join('<tr class="%s"><td><a href="#comp-%s" class="letter">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><i class="sd %s"></i> %s</td><td><i class="sd %s"></i> %s</td><td><i class="sd %s"></i></td><td>%d/8</td></tr>' % (
            VCLS[verdict_of(c)], c.get("_letter"), c.get("_letter"), esc(str(c.get("address", "")).title()), esc(str(c.get("date", ""))), money(c.get("price")), esc(c.get("floor_m2") or "—"), ("%s m" % c.get("dist_m")) if c.get("dist_m") is not None else "—",
            _sd(c, "slope"), esc(c.get("level") if c.get("level") not in (None, "") else "—"), _sd(c, "land"), esc(c.get("cars") if c.get("cars") not in (None, "") else "—"), _sd(c, "condition"), completeness(c)) for c in cp.get("items", []))
    else:
        _rows = None
    matrix = '<h3 style="margin-top:0">%s</h3><div class="tw"><table class="mx"><tr>%s</tr>%s</table></div>' % (t("matrix_h"), "".join("<th>%s</th>" % x for x in mth), "".join(
        '<tr class="%s"><td><a href="#comp-%s" class="letter">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><i class="sd %s"></i></td><td><i class="sd %s"></i></td><td><i class="sd %s"></i></td><td>%d/8</td></tr>' % (
            VCLS[verdict_of(c)], c.get("_letter"), c.get("_letter"), esc(str(c.get("address", "")).title()), esc(str(c.get("date", ""))), money(c.get("price")), c.get("p_lv") or "—", ("%s m" % c.get("dist_m")) if c.get("dist_m") is not None else "—",
            {1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get("land"))], {1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get("slope"))], {1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get("condition"))], completeness(c)) for c in cp.get("items", [])))
    if _rows is not None:
        matrix = '<h3 style="margin-top:0">%s</h3><div class="tw"><table class="mx"><tr>%s</tr>%s</table></div>' % (t("matrix_h"), "".join("<th>%s</th>" % x for x in mth), _rows)
    mp = svg_map(cp.get("items", [])); mp = ("<h3>%s</h3>%s" % (t("map_h"), mp)) if mp else ""
    scat = svg_scatter(cp.get("items", []), subj, summ.get("range"))
    scat = matrix + '<div class="two">' + (("<div><h3>%s</h3>%s<p class=\"note\">%s</p></div>" % (t("scatter_h"), scat, t("scatter_note"))) if scat else "<div></div>") + "<div>" + mp + "</div></div>"
    plvh = ""
    if plv and not UNIT:   # P/LV cross-check is a land-value test; meaningless for strata units
        plvh = "<h3>%s</h3><p>%s</p>" % (t("plv_h"), esc(cp.get("p_lv_note", "")) or ("%d comps, P/LV %.2f–%.2f, median %.2f" % (len(plv), plv[0], plv[-1], statistics.median(plv))))
    pr = d.get("pricing", {}); prh = "<h3>%s</h3><p>%s</p>" % (t("pricing_h"), esc(pr.get("method_note", "")))
    if pr.get("upper") or pr.get("lower"):
        prh += "<ul><li><b>%s:</b>%s</li><li><b>%s:</b>%s</li></ul>" % (t("bk_upper"), esc(pr.get("upper", "")), t("bk_lower"), esc(pr.get("lower", "")))
    if pr.get("widen_reason"):
        prh += '<p class="warn">%s</p>' % esc(pr["widen_reason"])
    mg = pr.get("mortgage") or {"rate": 0.0615, "years": 30, "step": 50000}
    _mr = float(mg.get("rate", 0.0615)) / 12; _mn = int(mg.get("years", 30)) * 12
    _pay = lambda P: P * _mr / (1 - (1 + _mr) ** (-_mn)) if P else None
    _three = [(t("offer_first"), summ.get("offer", {}).get("first")), (t("mort_list"), subj.get("list_price")), (t("offer_walk"), summ.get("offer", {}).get("walk_away"))]
    _three = [(k, _pay(float(v))) for k, v in _three if v]
    prh += ("<h3>%s</h3>%s" % (t("mort_h"), svg_bars([v for k, v in _three], [k for k, v in _three], fmt=(lambda v: money(v) + ("/月" if LANG == "zh" else "/mo")), h=170, highlight_last=False))) if _three else ""
    r = float(mg.get("rate", 0.0615)) / 12; n = int(mg.get("years", 30)) * 12; step = float(mg.get("step", 50000))
    delta = step * r / (1 - (1 + r) ** (-n)) if r > 0 else step / n
    prh += "<p>%s</p><p>%s</p>" % (t("mortgage", step=money(step), delta=money(delta), rate=float(mg.get("rate", 0.0615)) * 100, years=int(mg.get("years", 30))),
                                  esc(pr.get("bank_valuation_note")) or t("bank_val"))
    manual.append(("bank valuation", t("bank_val")))
    S.append(sec("s5", scat + "<p>%s</p><p class=\"note\">%s %s</p>%s%s%s" % (t("comp_lead"), esc(cp.get("source_note", "")), esc(cp.get("filter_note", "")), cards_html, plvh, prh)))

    # ---- 6 future
    fchips = '<h3 style="margin-top:0">%s</h3><div class="chips">%s</div>' % (t("future_chips"), "".join(
        '<span class="chip %s" title="%s">%s · %s</span>' % (cls_of(f.get("status", "na")) or "na", esc(f.get("basis", "")), esc(f.get("path", "")), esc(f.get("conclusion", ""))) for f in d.get("future", [])))
    fu = d.get("future", []); fth = tt("future_th"); frows = ""
    for f in fu:
        if f.get("next"): manual.append((f.get("path"), f["next"]))
        frows += '<tr><td>%s</td><td class="%s">%s</td><td>%s</td><td>%s</td></tr>' % (esc(f.get("path")), cls_of(f.get("status")), esc(f.get("conclusion")), esc(f.get("basis")), nextcell(f.get("next", "")))
    S.append(sec("s6", fchips + "<table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>%s</table><p class=\"note\">%s</p>" % (fth[0], fth[1], fth[2], fth[3], frows, esc(d.get("future_note", "")))))

    # ---- 7 market (chart first, table folded as the data source)
    mk = d.get("market", {}); left = right = ""
    vac = mk.get("vacancy", {})
    if vac.get("rows"):
        rows = vac["rows"][-36:]
        left += "<h3>%s(%s)</h3>%s%s<p class=\"note\">%s</p>" % (t("vac_h"), esc(vac.get("scope", "")),
            svg_line([[float(r[2]) for r in rows]], ["%d-%02d" % (r[0], r[1]) for r in rows], pct=True, h=200),
            tbl_src("<table><tr><th>Month</th><th>%%</th><th>vacant / total</th></tr>%s</table>" % "".join("<tr><td>%d-%02d</td><td>%.2f%%</td><td>%s / %s</td></tr>" % (r[0], r[1], float(r[2]), r[3] if len(r) > 3 else "", r[4] if len(r) > 4 else "") for r in rows[-12:])),
            esc(vac.get("note", "")))
    som = mk.get("som", {})
    if som.get("rows"):
        rows = som["rows"][-36:]
        left += "<h3>%s</h3>%s%s<p class=\"note\">%s</p>" % (t("som_h"),
            svg_line([[r[2] for r in rows], [r[3] for r in rows]], ["%d-%02d" % (r[0], r[1]) for r in rows], names=["Houses", "Units"], h=200),
            tbl_src("<table><tr><th>Month</th><th>Houses</th><th>Units</th><th>Total</th></tr>%s</table>" % "".join("<tr><td>%d-%02d</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (r[0], r[1], r[2], r[3], (r[2] or 0) + (r[3] or 0)) for r in rows[-12:])),
            esc(som.get("note", "")))
    left += "<h3>Days on market</h3><p>%s</p>" % esc(mk.get("dom_note", ""))
    if not dom.get("suburb_median_dom"): left += paid("days-on-market", "Days on market")
    gr = mk.get("growth", {}); gth = tt("growth_th")
    if gr.get("rows"):
        th30 = gr.get("thirty", {})
        hb = [(g.get("period"), float(g["ann"]) if g.get("ann") is not None else None, "") + ((g["kind"],) if g.get("kind") else ()) for g in gr["rows"]]
        if th30: hb.append((t("thirty"), None, th30.get("text", "")[:40] + ("…" if len(th30.get("text", "")) > 40 else "")))
        right += "<h3>%s</h3>%s%s%s<p class=\"note\">%s</p>" % (t("growth_h"), svg_hbars(hb, fmt=lambda v: "%.1f%% p.a." % v), kind_legend({g.get("kind") for g in gr["rows"]}),
            tbl_src("<table><tr>%s</tr>%s<tr><td>%s</td><td colspan=\"4\" class=\"%s\">%s</td></tr></table>" % ("".join("<th>%s</th>" % x for x in gth),
                 "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s%%</td><td>%s%%</td></tr>" % (esc(g.get("period")), money(g.get("start")), money(g.get("current")), g.get("cum"), g.get("ann")) for g in gr["rows"]),
                 t("thirty"), "na" if th30.get("status", "none") == "none" else "", esc(th30.get("text", "")))), esc(gr.get("note", "")))
    if mk.get("yearly"):
        ys = sorted(mk["yearly"].items())
        right += "<h3>%s</h3>%s%s" % (t("yearly_h"), svg_line([[(v[0] or None) for y, v in ys]], [str(y)[-2:] if i % 2 else str(y) for i, (y, v) in enumerate(ys)], fmt=money, h=200),
            tbl_src("<table><tr><th>Year</th><th>Median</th><th>n</th></tr>%s</table>" % "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (y, money(v[0]) if v[0] else "—", v[1]) for y, v in ys)))
    if mk.get("ask") or mk.get("rent"):
        right += "<h3>%s</h3>" % t("ask_h")
        if mk.get("ask"):
            rows = mk["ask"]
            right += svg_line([[num(r[1]) for r in rows], [num(r[2]) if len(r) > 2 else None for r in rows]], [str(r[0])[5:] for r in rows], names=["Houses", "3-bed"], fmt=money, h=180, hline=((t("nav_list") + " " + money(subj.get("list_price")), num(subj.get("list_price"))) if subj.get("list_price") else None))
            right += tbl_src("<table><tr><th>Week</th><th>Houses (mean asking)</th><th>3-bed</th></tr>%s</table>" % "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (r[0], money(r[1]), money(r[2]) if len(r) > 2 else "") for r in rows[-8:]))
        if mk.get("rent"): right += "<p class=\"note\">%s</p>" % esc(mk.get("rent_note", ""))
    hold = d.get("holding", {}); sc_ = d.get("school_commute", {})
    extra = ""
    if hold:
        extra += "<h3>%s</h3><table>%s</table><p class=\"note\">%s</p>" % (t("holding_h"), "".join("<tr><th>%s</th><td>%s</td></tr>" % (esc(k), esc(v)) for k, v in hold.get("rows", [])), esc(hold.get("source_note", "")))
    if sc_:
        extra += "<h3>%s</h3><table>%s</table>" % (t("school_h"), "".join("<tr><th>%s</th><td>%s</td></tr>" % (esc(k), esc(v)) for k, v in sc_.get("rows", [])))
        if sc_.get("next"): manual.append(("school/commute", sc_["next"])); extra += nextcell(sc_["next"])
    S.append(sec("s7", '<div class="two"><div>%s</div><div>%s</div></div>%s' % (left, right, extra)))

    # ---- 8 next steps
    qs = d.get("questions", []); qh = "<h3>%s</h3>" % t("q_h") + "".join('<div class="q">%s<span class="en">%s</span></div>' % (esc(q.get("zh") if LANG == "zh" else q.get("en")), esc(q.get("en") if LANG == "zh" else q.get("zh", ""))) for q in qs)
    if UNIT:
        _bbd = list(DEFAULT_BEFORE_BUY_UNIT[LANG])
        if _flood_cond(d, scards): _bbd.insert(-1, BB_FLOOD_UNIT[LANG])
    else:
        _bbd = DEFAULT_BEFORE_BUY[LANG]
    bb = d.get("before_buy") or [{"item": a, "why": b, "who": c} for a, b, c in _bbd]
    bth = tt("bb_th")
    bbh = "<h3>%s</h3><table><tr><th>%s</th><th>%s</th><th>%s</th></tr>%s</table>" % (t("bb_h"), bth[0], bth[1], bth[2], "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(b.get("item")), esc(b.get("why")), esc(b.get("who"))) for b in bb))
    for b in bb: manual.append((b.get("item"), "%s(%s)" % (b.get("why", ""), b.get("who", ""))))
    ck = d.get("inspection_checklist") or (DEFAULT_CHECKLIST_UNIT if UNIT else DEFAULT_CHECKLIST)[LANG]
    ckh = "<h3>%s</h3><ol>%s</ol>" % (t("ck_h"), "".join("<li>%s</li>" % esc(x) for x in ck))
    br = d.get("briefs", {})
    sol = br.get("solicitor") or default_brief("solicitor", d)
    insp = br.get("inspector") or default_brief("inspector", d)
    brh = "<h3>%s</h3><div class=\"brief\">%s</div><h3>%s</h3><div class=\"brief\">%s</div>" % (t("brief_sol"), esc(sol), t("brief_insp"), esc(insp))
    for m in d.get("manual_items", []): manual.append((m.get("item"), "%s(%s · %s)" % (m.get("what", ""), m.get("who", ""), m.get("where", ""))))
    seen = set(); mrows = ""
    for k, v in manual:
        key = (str(k), str(v))
        if key in seen or not v: continue
        seen.add(key); mrows += "<li><b>%s</b> — %s</li>" % (esc(k), esc(v))
    mh = "<h3>%s</h3><ul>%s</ul>" % (t("manual_h"), mrows)
    _names = []
    for k, v in manual:
        if v and k and str(k) not in _names: _names.append(str(k))
    _lnk = lambda u: '<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(u), esc(u))
    _shown = ("、" if LANG == "zh" else ", ").join(_names[:5]) or "—"
    if len(_names) > 5: _shown += t("n_more", n=len(_names) - 5)
    mh += '<p class="needs-person">%s</p>' % t("needs_person", list=esc(_shown))
    if meta.get("show_booking") is True or str(meta.get("show_booking")).lower() == "true":
        mh += '<p class="needs-person">%s</p>' % t("booking", url=_lnk(BOOKING[LANG]))
    S.append(sec("s8", '<div class="two"><div>%s</div><div>%s</div></div>%s%s%s' % (qh, bbh, ckh, brh, mh)))

    # ---- 9 glossary
    gl = d.get("glossary", [])
    glh = '<dl class="gl">%s</dl>' % "".join("<dt>%s</dt><dd>%s%s</dd>" % (esc(g.get("term")), esc(g.get("text")), (' <a href="%s">source</a>' % esc(g["url"])) if g.get("url") else "") for g in gl)
    bl = d.get("blockers", []) if (meta.get("edition") or "public").lower() == "internal" else []
    if bl:
        glh += "<h3>%s</h3><table><tr><th>#</th><th>Step</th><th>Issue</th><th>Workaround</th></tr>%s</table>" % (t("blockers_h"), "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(b.get("n")), esc(b.get("step")), esc(b.get("issue")), esc(b.get("workaround"))) for b in bl))
    S.append(sec("s9", glh))

    # ---- counts + footer
    n_desk = sum(1 for h in hz if h.get("tier", "covered") == "covered") + len(fu) + len(gr.get("rows", [])) + len(data_cards) + (1 if items else 0) + (1 if vac.get("rows") else 0) + (1 if som.get("rows") else 0)
    m_manual = len(seen)
    _tot = max(1, n_desk + m_manual)
    countbar = '<div class="countbar">%s<div class="pbar"><span style="width:%.0f%%"></span></div></div>' % (t("countbar", n=n_desk, m=m_manual), 100.0 * n_desk / _tot)
    disc = '<div class="disclaimer-end">%s%s</div>' % ("".join('<p class="note">%s</p>' % esc(x[0]) for x in DISCLAIMER_END), "".join('<p class="note" lang="en">%s</p>' % esc(x[1]) for x in DISCLAIMER_END))
    _video = meta.get("video_url") or VIDEO_DEFAULT
    foot = countbar + disc + '<div class="foot">%s<br>%s<br>%s</div>' % (
        t("attrib", video=_lnk(_video)),
        (t("foot_time3", h=meta.get("human_minutes", "?"), a=meta.get("active_minutes", "?"), w=meta.get("wall_minutes", "?")) if meta.get("active_minutes") or meta.get("wall_minutes") else t("foot_time", h=meta.get("human_minutes", "?"), mc=meta.get("machine_minutes", "?"))), t("foot_gen", date=date))
    return title, banner, summary, "\n".join(S), foot, warnings

def _flood_card(d, cards=None):
    cards = cards or (d.get("summary", {}).get("cards") or d.get("status_cards") or [])
    return next((c for c in cards if re.search(r"洪水|flood", str(c.get("label", "")), re.I)), None)
def _flood_cond(d, cards=None):
    fc = _flood_card(d, cards)
    if fc and fc.get("status") == "cond": return True
    return any(h.get("status") == "cond" and re.search(r"洪水|flood", str(h.get("item", "")), re.I) for h in d.get("hazards", []))
def default_brief_unit(kind, d):
    s = d.get("subject", {}); addr = s.get("address", ""); fc = _flood_card(d) or {}
    fl = ("%s %s" % (fc.get("value", ""), ("(" + str(fc["note"])[:120] + ")") if fc.get("note") else "")).strip() or ("未查到" if LANG == "zh" else "not found")
    lv = (s.get("land_value") or {}).get("latest"); lvt = money(lv) if lv else ("(无免费数据)" if LANG == "zh" else "(no free figure)")
    if LANG == "zh":
        if kind == "solicitor":
            return ("您好,我在考虑购买 %s(strata 单元,%s),请在审合同时重点核对:\n1. Strata 报告(NSW s 184 证书 / WA precontractual disclosure):欠费、纠纷、在办工程。\n2. Levies 历史、special levy、维修基金余额与 10 年资本工程计划。\n3. By-laws:宠物、短租、装修限制。\n4. 楼栋缺陷、保险理赔、诉讼记录;cladding 状况;楼栋保险估值与免赔额。\n5. 洪水:我查到的结果是 %s;请核对规划证书 / 披露文件里的洪水标注,以及 strata 保险是否承保洪水。\n6. 母地块地价 %s 是整栋基地的;本单元的 unit entitlement 是多少,车位与储物是否在本 lot 产权内(lot/plan:%s)。\n7. 合同特殊条款、押金、冷静期与交割期。\n谢谢。"
                    % (addr, s.get("dwelling", ""), fl, lvt, s.get("lot_dp", "—")))
        return ("您好,我在考虑购买 %s(%s 年建,%s),验房时请重点看:\n1. 单元内部:墙面与天花裂缝、门窗开关、地面平整。\n2. 阳台:防水、瓷砖空鼓、排水、栏杆。\n3. 湿区(浴室、厨房、洗衣):渗漏、霉斑、防水层失效迹象。\n4. 从本单元能看到的公共部分:外墙、走廊、地库与本套车位的水渍与裂缝。\n5. 请把照片和维修估价分级(必修 / 建议 / 观察)写进报告。\n谢谢。"
                % (addr, s.get("built", "—"), s.get("dwelling", "")))
    if kind == "solicitor":
        return ("Hi, I am considering %s (a strata unit, %s). When reviewing the contract please check:\n1. The strata report (NSW s 184 certificate / WA precontractual disclosure): arrears, disputes, works in progress.\n2. Levies history, special levies, sinking-fund balance and the 10-year capital works plan.\n3. By-laws: pets, short stays, renovation limits.\n4. Building defects, insurance claims, litigation; cladding status; the building insurance valuation and excess.\n5. Flood: my desktop result is %s; please check the flood notations in the planning certificate / disclosure and whether the strata policy covers flood.\n6. The parent-lot land value %s is for the whole site; what is this unit's entitlement, and are the car space and storage on this lot's title (lot/plan: %s)?\n7. Special conditions, deposit, cooling-off and settlement.\nThanks." % (addr, s.get("dwelling", ""), fl, lvt, s.get("lot_dp", "—")))
    return ("Hi, I am considering %s (built %s, %s). For the inspection please focus on:\n1. The apartment interior: wall and ceiling cracks, doors and windows, floor levels.\n2. Balconies: waterproofing, drummy tiles, drainage, balustrades.\n3. Wet areas (bathrooms, kitchen, laundry): leaks, mould, signs of membrane failure.\n4. Common property visible from the lot: façade, corridors, the basement and this unit's car space (water marks, cracking).\n5. Please grade repairs (must / should / watch) with photos and cost estimates.\nThanks." % (addr, s.get("built", "—"), s.get("dwelling", "")))

def default_brief(kind, d):
    if UNIT: return default_brief_unit(kind, d)
    s = d.get("subject", {}); addr = s.get("address", ""); summ = d.get("summary", {})
    hz = [h for h in d.get("hazards", []) if h.get("status") in ("warn", "bad")]
    flags = "; ".join("%s: %s" % (h.get("item"), h.get("result") or "") for h in hz) or ("无" if LANG == "zh" else "none")
    if LANG == "zh":
        if kind == "solicitor":
            return ("您好,我在考虑购买 %s,请在审合同时重点核对:\n1. Section 10.7 证书上的洪水、山火、滑坡、heritage 标注是否与我的桌面尽调一致(我查到的标注:%s)。\n2. 合同附的 title / plan:Lot/DP 与 %s 一致;有无 easement、covenant、挡土或排水负担。\n3. 规划条文(分区、最小地块、双拼/附属住宅门槛)请按现行版复核,我引用的是存档快照。\n4. 若带租约:租约类型、到期日、租金、能否空置交割。\n5. 合同特殊条款、押金、冷静期与交割期。\n谢谢。"
                    % (addr, flags, s.get("lot_dp", "—")))
        return ("您好,我在考虑购买 %s(%s 年建,%s),预约 Building & Pest 时请重点看:\n1. 坡地与挡土:%s。排水走向、地基沉降、挡土墙状况。\n2. 潮气与白蚁(底层、屋顶空间)。\n3. 外墙与屋顶材料,是否含石棉(建年 %s)。\n4. 加建部分是否有审批痕迹。\n5. 请把照片和维修估价分级(必修 / 建议 / 观察)写进报告。\n谢谢。"
                % (addr, s.get("built", "—"), s.get("dwelling", ""), summ.get("max_risk", "")[:80], s.get("built", "—")))
    if kind == "solicitor":
        return ("Hi, I am considering %s. When reviewing the contract please check:\n1. The Section 10.7 certificate notations for flood, bushfire, landslip and heritage against my desktop research (I found: %s).\n2. Title/plan: Lot/DP matches %s; any easements, covenants, retaining or drainage burdens.\n3. Planning clauses (zone, minimum lot, dual-occupancy / secondary-dwelling thresholds) against the current version — I relied on an archived snapshot.\n4. If leased: lease type, expiry, rent, vacant possession.\n5. Special conditions, deposit, cooling-off and settlement.\nThanks." % (addr, flags, s.get("lot_dp", "—")))
    return ("Hi, I am considering %s (built %s, %s). For the building & pest inspection please focus on:\n1. Slope and retaining: %s. Drainage path, footing movement, retaining walls.\n2. Damp and termites (subfloor, roof space).\n3. Wall and roof materials, possible asbestos (built %s).\n4. Any unapproved additions.\n5. Please grade repairs (must / should / watch) with photos and cost estimates.\nThanks." % (addr, s.get("built", "—"), s.get("dwelling", ""), summ.get("max_risk", "")[:80], s.get("built", "—")))

SCHEMA = """data.json fields (all optional unless marked *):
meta: lang zh|en, title, date*, one_liner, session_resume_url, edition public|internal (public = thumbnails + links only; internal = carousel + before/after), human_minutes, active_minutes, wall_minutes (machine_minutes kept for old files), video_url (footer link; default the YouTube channel), show_booking true|false (default false: no booking line)
subject*: address*, lot_dp, land_m2*, list_price*, built, dwelling, title_type torrens|strata|community, strata_m2 (unit: strata lot area incl. balcony/car/storage; shown instead of land), beds, baths, cars, floor_m2, status_line, status_class ok|warn|bad (hero panel), facts [[label, value], ...] (overview grid), land_value {latest, date, history {year: value}}
photos: images [{url, caption}] (hot-linked from the listing site's own URLs exactly as served, credited, never downloaded), credit_source, before_after [{before, after, caption}] (internal edition only), sources [{name, url, crosscheck}], streetview_url, material_from_photos
summary*: verdict_line*, max_risk*, range [lo, hi]*, range_note, avm_range [lo, mid, hi] (free Domain estimate, optional), offer {first, walk_away, confidence, confidence_note},
          cards: 5 x {label, status ok|warn|bad|cond|na, value, note, next}  (preferred over status_cards; if both absent, five placeholder cards with the default labels are shown —
                 house: flood / bushfire / landslip category / measured slope / development potential; unit: flood (basement/lobby) / bushfire / noise & arterial roads / strata health check / planning & supply)
status_cards: same shape as summary.cards (older files; still read)  (flood: bad = mainstream / High–Medium hit = veto; cond = Overland Flow / Low-PMF hit = conditional)
UNIT MODE: on when subject.title_type == "strata", subject.dwelling contains unit/apartment/flat/公寓/单元, or lot_dp contains an SP number.
  It relabels the hero area (strata lot) and land value (parent lot, entitlement needs a person), scores (land -> area & cars, slope -> level·aspect·view),
  completeness (floor_m2, cars, level, orientation|aspect, built, reno, levies, date & price; bookend needs >= 4/8), comps chart x = floor_m2,
  hides the P/LV block, and titles section 4 "Parent lot & building" with neutral figure captions (site_svg = Figure A, profile_svg = Figure B).
timeline: [{date, event, source}]
dom: months_approx, basis, suburb_median_dom, suburb_dom_source, price_history_text, price_history_status verified|unverified
ruler: prices [..], list, window_label, n, median, min, max
hazards*: [{item, status ok|warn|bad|cond|na, tier covered|uncovered|paid, result, source, date, note, next*, slug}]  (status cond adds the two fixed flood next steps automatically)
land: facts [[label, value]], site_svg (file path or inline <svg>), profile_svg, profile_flat {street, rear, fall} (replaces the profile chart on flat sites), lv_note, street_sales [{addr, price, date, land, floor_m2 (unit mode: bubble size)}]
comps: source_note, filter_note, subject {land_m2}, p_lv_note, items (lettered A, B, C… in order) [{address, price, date, dist_m, lon, lat, land_m2, lv, lv_m2, p_lv, landslip, street_side, elev, beds, baths, floor_m2, built, storeys, wall, reno,
       level, orientation (or aspect), view, cars, levies (unit fields),
       scores {land, slope, condition: +1|0|-1|null}, verdict (optional override; all three scores null -> "Unknown": grey, collapsed, never a bookend), bookend upper|lower|null, note}]
pricing: method_note, upper, lower, widen_reason, mortgage {rate, years, step}, bank_valuation_note
future: [{path, status, conclusion, basis, next}], future_note
market: vacancy {scope, rows [[y,m,pct,vacant,total]], avg12, note}, som {rows [[y,m,houses,units]], note}, dom_note, growth {rows [{period,start,current,cum,ann,kind house|unit|building (optional; colours the bar, legend when mixed)}], thirty {status none|suburb|city, text}, note}, ask [[date,houses,3bed]], rent_note, yearly {year: [median, n]}
holding: rows [[label, value]], source_note
school_commute: rows [[label, value]], next
questions: [{zh, en}]
before_buy: [{item, why, who}] (default list used if absent)
inspection_checklist: [str] (default used if absent)
briefs: {solicitor, inspector} (default templates if absent)
manual_items: [{item, what, who, where}]
glossary: [{term, text, url}]
blockers: [{n, step, issue, workaround}]
"""

def main():
    ap = argparse.ArgumentParser(description="auspptdd report generator: data.json -> HTML")
    ap.add_argument("--data", help="path to data.json")
    ap.add_argument("--out", help="output .html path")
    ap.add_argument("--lang", choices=["zh", "en"], help="override meta.lang")
    ap.add_argument("--template", default=os.path.join(HERE, "..", "templates", "report.html"))
    ap.add_argument("--schema", action="store_true", help="print the data.json field list and exit")
    a = ap.parse_args()
    if a.schema:
        print(SCHEMA); return
    if not a.data or not a.out:
        ap.error("--data and --out are required (or use --schema)")
    global LANG
    d = json.load(open(a.data, encoding="utf-8")); d["_path"] = os.path.abspath(a.data)
    if a.lang: d.setdefault("meta", {})["lang"] = a.lang
    title, banner, summary, sections, foot, warnings = build(d)
    tpl = open(a.template, encoding="utf-8").read()
    out = (tpl.replace("{{LANG}}", "zh-CN" if LANG == "zh" else "en").replace("{{TITLE}}", esc(title)).replace("{{BANNER}}", banner)
           .replace("{{SUMMARY}}", summary).replace("{{SECTIONS}}", sections).replace("{{FOOTER}}", foot)
           .replace("{{EXPAND_ALL}}", t("expand_all")).replace("{{COLLAPSE_ALL}}", t("collapse_all")).replace("{{TOOLBAR_HINT}}", t("toolbar_hint")))
    open(a.out, "w", encoding="utf-8").write(out)
    for w in warnings: print("WARNING:", w, file=sys.stderr)
    print("written", a.out, len(out), "bytes")

if __name__ == "__main__":
    main()
