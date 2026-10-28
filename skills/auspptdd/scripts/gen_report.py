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
  python gen_report.py --data data.json --check   # list standard figures data.json cannot produce (writes nothing)

Windows: the script forces UTF-8 on stdout/stderr and every open(); no PYTHONUTF8 needed.
No third-party packages.
"""
import sys, os, json, re, html, math, argparse, datetime, statistics, urllib.parse

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
 "scatter_note": ("点色 = 三项打分结论(红 优于 / 金 相当 / 绿 逊于);粗环 = 上下限参考;★ = 标的(标价);绿带 = 合理区间。", "Dot colour = three-score verdict (red superior / gold close / green inferior); thick ring = reference bound; ★ = subject at list price; green band = fair range."),
 "dom_bars_h": ("在市时长对比", "Days on market, compared"), "dom_this": ("本套(约)", "This property (approx.)"), "dom_sub": ("区均(不是本套)", "Suburb median (not this one)"),
 "mort_h": ("三个价位的月供(按 {lvr}% 贷款)", "Repayment at the three prices (at {lvr}% LVR)"), "mort_list": ("标价", "List"),
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
 "profile_flat": ("地块平坦:街面 {s} m → 后边界 {r} m,落差 {f} m。", "Flat site: street {s} m → rear {r} m, fall {f} m."),
 "map_real_h": ("可比地图(★ 标的;字母 = 可比;地块边界为官方地籍)", "Map of comparables (★ subject; letters = comparables; lot boundary from the cadastre)"),
 "map_attrib": ("底图 © OpenStreetMap 贡献者;离线时显示相对位置图。", "Base map © OpenStreetMap contributors; the relative-position chart shows when offline."),
 "map_failed": ("地图未加载,已改用相对位置图。", "Map did not load; showing the relative-position chart instead."),
 "map_gmaps": ("在 Google 地图中打开标的 ↗", "Open the subject in Google Maps ↗"),
 "open_profile": ("打开物业档案页 ↗", "Open the property profile ↗"),
 "figs_missing": ("本次未能生成的标准图件", "Standard figures not produced this run"),
 "offer_disclaimer": ("首次出价与放手价只是按公开数据推出的<b>参考锚点</b>,不是建议成交价,也不是估值。实际出价要按当时的市场环境、买家需求、同场竞价买家的数量与强度、卖方的出售动机与时间压力动态调整;拍卖或多方竞价时尤其如此。出价前请把这两个数字与你的预算、贷款预批和律师 / 买方代理的意见放在一起核。",
                      "The first offer and walk-away price are <b>reference anchors</b> derived from public data, not a recommended purchase price and not a valuation. Adjust them to the market at the time, buyer demand, how many competing buyers are in the room and how strong they are, and the seller's motivation and time pressure — especially at auction or in multi-offer situations. Check both numbers against your budget, loan pre-approval and your solicitor / buyer's agent before offering."),
 "tl_strip_note": ("按真实时间比例。形状 = 事件类型(● 成交 · ◆ 出租 · ▲ 挂牌 · ▼ 调价 · 小圆点 其它);点上方数字 = 价格,下方 = 日期;红 = 现在挂牌,? = 待核实的记录。",
                   "True time scale. Shape = event type (● sale · ◆ rented · ▲ listed · ▼ price change · small dot other); number above the marker = price, date below; red = current listing, ? = record to verify."),
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
 "comp_lead": ("可比先于区间:先逐张打分,再定上下限参考,最后出合理区间。标签只按三项打分——土地 / 坡度与街面侧 / 房况(建年、面积、建材、翻新);价格只当结果摆旁边。默认只展开「相当」与上下限参考两张,其余点开看;上下限只是参考,不是出价的硬边界。",
               "Comparables come before the range: score each card, pick the upper / lower reference bounds, then set the range. Labels come only from three scores — land / slope & street side / condition (year, area, material, renovation); price is shown beside as a result. Only 'Close' cards and the two reference bounds are open by default; they are references, not hard limits for your offer."),
 "v_sup": ("优于", "Superior"), "v_close": ("相当", "Close"), "v_inf": ("逊于", "Inferior"),
 "bk_upper": ("上限参考", "Upper reference"), "bk_lower": ("下限参考", "Lower reference"),
 "completeness": ("数据完整度", "Data completeness"),
 "cg_basic": ("基本", "Basics"), "cg_price": ("价格与比率", "Price & ratios"), "cg_cmp": ("与标的比较(三项打分)", "Versus subject (three scores)"), "cg_verdict": ("结论", "Verdict"),
 "sc_land": ("土地", "Land"), "sc_slope": ("坡度/街面侧", "Slope/street side"), "sc_cond": ("房况", "Condition"),
 "sc_better": ("优", "better"), "sc_same": ("同", "same"), "sc_worse": ("逊", "worse"), "sc_unknown": ("未知", "unknown"),
 "bk_low_warn": ("该上/下限参考的数据完整度低于 5/8,不符合要求;区间已加宽并说明。", "This reference bound has completeness below 5/8 and does not qualify; the range was widened and the reason stated."),
 "plv_h": ("成交价 / 官方地价 倍数交叉检验", "Sale price ÷ land value cross-check"),
 "pricing_h": ("合理区间怎么来的", "How the range was derived"),
 "mortgage": ("按 {lvr}% 贷款,房价每差 {step} 即贷款差 {loan},月供约差 {delta}/月(假设利率 {rate:.2f}%、{years} 年本息同还;公式 P·r/(1−(1+r)^−n),r = 月利率,n = 月数)。",
              "At {lvr}% LVR, each {step} of price is {loan} of loan and moves the repayment by about {delta}/month (assumes {rate:.2f}% p.a., {years}-year principal & interest; P·r/(1−(1+r)^−n), r = monthly rate, n = months)."),
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
 "bk_unk_warn": ("三项打分全部未知,不能作上下限参考。", "All three scores are unknown; this card cannot be an upper / lower reference."),
 "growth_kind": ({"house": "独立屋", "unit": "公寓/单元", "building": "本楼"}, {"house": "House", "unit": "Unit", "building": "This building"}),
 # unit-mode variants: t(k) picks k + "_u" automatically when UNIT is on
 "s4_u": ("4. 母地块与楼栋 Parent lot & building", "4. Parent lot & building"),
 "f_land_u": ("m² 产权面积", "m² strata lot"),
 "k_lv_u": ("母地块地价", "Parent-lot land value"), "k_lv_val": ("{v}(份额需人)", "{v} (entitlement: needs a person)"),
 "sc_land_u": ("面积与车位", "Area & cars"), "sc_slope_u": ("楼层·朝向·景观", "Level·aspect·view"),
 "comp_lead_u": ("可比先于区间:先逐张打分,再定上下限参考,最后出合理区间。标签只按三项打分——面积与车位 / 楼层·朝向·景观 / 房况(建年、翻新、楼栋状况);价格只当结果摆旁边。排序:同竖列(同户型、同朝向)成交最优先,其次同楼,再次同郊区同卧室数、建筑面积 ±20%、18 个月内。默认只展开「相当」与上下限参考两张,其余点开看;上下限只是参考,不是出价的硬边界。",
                 "Comparables come before the range: score each card, pick the upper / lower reference bounds, then set the range. Labels come only from three scores — area & cars / level·aspect·view / condition (year, renovation, building condition); price is shown beside as a result. Ranking: same-stack sales (same floor plan, same aspect) first, then the same building, then the same suburb with the same bedrooms, floor area within ±20% and sold within 18 months. Only 'Close' cards and the two reference bounds are open by default; they are references, not hard limits for your offer."),
 "bk_low_warn_u": ("该上/下限参考的数据完整度低于 4/8,不符合要求;区间已加宽并说明。", "This reference bound has completeness below 4/8 and does not qualify; the range was widened and the reason stated."),
 "scatter_h_u": ("可比一图:建筑面积 × 成交价", "Comparables in one chart: floor area × sale price"),
 "matrix_th_u": (("#", "地址", "成交", "价", "面积 m²", "距离", "楼层", "车位", "房况", "完整度"), ("#", "Address", "Sold", "Price", "Floor m²", "Dist", "Level", "Cars", "Cond.", "Compl.")),
 "street_scatter_h_u": ("同街/同楼成交:时间 × 价格(气泡 = 建筑面积)", "Same-street sales: date × price (bubble = floor area)"),
 "lv_h_u": ("母地块地价 5 年史(整栋基地,不是本单元)", "Parent-lot land value, 5 years (whole site, not this unit)"),
 "fig_a": ("图 A", "Figure A"), "profile_h_u": ("图 B", "Figure B"),
 "ruler_lead_u": ("<b>价格标尺</b>——{window} 该郊区成交 {n} 笔(口径见数据说明),中位 {median};标价 {list} 位于其中:",
                  "<b>Price ruler</b> — {n} sales in {window} (scope as noted in the data), median {median}; the list price {list} sits here:"),
 "u_level": ("楼层", "Level"), "u_cars": ("车位", "Cars"), "u_aspect": ("朝向", "Aspect"), "u_levies": ("Strata 费", "Levies"),
 "u_floor": ("建筑", "Floor"), "u_pm2": ("$/m² 建筑", "$/m² floor"),
 # ---- v0.4.1 additions
 "offer_tbd": ("需结合与中介沟通后的信息定夺", "Set after the conversation with the agent"),
 "src_chips": ("来源核对:", "Sources checked:"),
 "widen_pref": ("区间说明:", "Range note:"),
 "ai_note": ("本节由 AI 按公开数据生成,没有人工判断,可能有误;请自行核实,并留意 AI 拿不到的信息(底价、卖家动机、竞争买家、未公开缺陷)。",
             "This section was generated by an AI from public data with no human judgement and may be wrong. Verify it yourself and remember what the AI cannot see: reserve price, vendor motivation, competing buyers, undisclosed defects."),
 "look_at": ("看什么:", "What to look at: "),
 "map_link": ("地图", "Map"), "sv_link": ("街景", "Street View"),
 "tlk_sale": ("成交", "Sale"), "tlk_rent": ("出租", "Rented"), "tlk_list": ("挂牌", "Listed"), "tlk_pc": ("调价", "Price change"),
 "tlk_other": ("其它", "Other"), "tlk_now": ("现在挂牌", "Current listing"), "tlk_q": ("待核实", "To verify"),
 "sub_tl": ("每个标记是一件事:上方数字是价格,下方是日期;看价格随时间往哪走,以及这次挂牌价与上一笔成交差多少。",
            "Each marker is one event: price above, date below. See which way prices moved over time and how far this listing sits from the last sale."),
 "ph_h": ("标价变化", "List-price changes"), "ph_list": ("标价", "List price"), "ph_band": ("合理区间", "Fair range"),
 "sub_steps": ("每一级台阶是一次调价;绿带是我们估计的合理区间,看现在的标价落在带内还是带外。",
               "Each step is one price change; the green band is our fair range. See whether the current list price sits inside or outside it."),
 "sub_scatter": ("标的(★)落在绿带的哪一段,土地更大的可比是否更贵;离绿带远的点要看原因(点开字母卡)。",
                 "Where the star sits in the green band, and whether comps with more land cost more; open the letter card of any dot far from the band."),
 "sub_scatter_u": ("标的(★)落在绿带的哪一段,面积更大的可比是否更贵;离绿带远的点要看原因(点开字母卡)。",
                   "Where the star sits in the green band, and whether larger comps cost more; open the letter card of any dot far from the band."),
 "sub_street": ("同街近期成交的价格有没有随时间上移;气泡越大地越大;红虚线是标价。",
                "Whether same-street prices are drifting up over time; bigger bubble = more land; the red dashed line is the list price."),
 "sub_map": ("可比离标的多远、在哪个方向;圈越外离得越远。红色 ★ 是标的。",
             "How far, and in which direction, the comparables sit from the subject; outer rings are further away. The red ★ is the subject."),
 "lg_subject": ("标的", "Subject"), "lg_bookend": ("上下限参考(粗环)", "Upper / lower reference (thick ring)"), "lg_rings": ("距离圈", "Distance rings"),
 "lg_sale": ("成交(气泡 = 土地面积)", "Sale (bubble = land area)"), "lg_sale_u": ("成交(气泡 = 建筑面积)", "Sale (bubble = floor area)"),
 "stack_h": ("同竖列 × 楼层", "Same stack × floor"), "bldg_h": ("同户型 × 成交日期", "Same layout × sale date"),
 "bsales_h": ("楼内全部成交(未筛选,按日期)", "All sales in the building (unfiltered, by date)"),
 "bsales_th": (("单元", "户型(房·卫·车)", "室内 m²", "价格", "日期", "来源"), ("Unit", "Layout (bd·ba·car)", "Floor m²", "Price", "Date", "Source")),
 "strata_tip": ("strata 地块,无独立土地面积", "strata lot, no separate land area"),
 "strata_note": ("标记为 strata 的行,土地一栏留空:strata 地块没有独立的土地面积。", "Rows marked strata leave the Land cell blank: a strata lot has no separate land area."),
 "map_same_bldg": ("可比全部在同一栋楼内,位置图省略;见第 4 节楼栋图。", "All comparables are in the same building; the map is omitted, see the building charts in section 4."),
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

_DUP_FACT_RE = re.compile(
    r"(?:address|地址|beds?|bedrooms?|baths?|bathrooms?|cars?|car\s*spaces?|parking|beds?\s*/\s*baths?(?:\s*/\s*cars?)?|几房|房型|户型|卧室|卫生间|车位"
    r"|built|year\s*built|建年|建成|建成年份|建成年代|建于|建造年份"
    r"|list(?:ing)?\s*price|asking\s*price|标价|挂牌价|last\s*sold|last\s*sale|previous\s*sale|上次成交|上一笔成交|上一次成交"
    r"|(?:domain\s*)?(?:avm|(?:price\s*)?estimate|估价|估值)|domain.*(?:估值|估价|estimate|avm))(?:\s*[\(（][^\)）]*[\)）])?", re.I)
def dup_fact(label):
    """True when an overview facts row repeats something the hero panel already shows"""
    return bool(_DUP_FACT_RE.fullmatch(re.sub(r"[:：\s]+$", "", str(label).strip())))
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
# ---------------------------------------------------------------- shared chart helpers (v0.4.1): label de-overlap, legend rows, marker shapes, subtitles
CW = 6.0   # approx px per Latin char at 10.5px; _tw() counts CJK as full width
def _tw(text, fs=10.5):
    return sum((fs if ord(ch) > 0x2E7F else fs * CW / 10.5) for ch in str(text))
def dodge(labels, step=12, direction=1, lo=None, hi=None, tries=6):
    """Greedy label de-overlap. labels: [{x, y (text baseline), text, anchor start|middle|end, fs?, dir?}].
    A label that clashes with an already placed one is pushed by `step` px (direction +1 = down, -1 = up) up to `tries` times.
    Sets lb['moved'], lb['y0'] and lb['ok'] (False = could not be placed inside [lo, hi]; the caller then draws no text, the marker keeps its <title>)."""
    placed = []
    for lb in sorted(labels, key=lambda q: (q["y"] * q.get("dir", direction), q["x"])):
        dr = lb.get("dir", direction); fs = lb.get("fs", 10.5); w = _tw(lb["text"], fs) + 4; a = lb.get("anchor", "middle")
        x0 = lb["x"] - (w if a == "end" else (w / 2 if a == "middle" else 0)); y = lb["y"]; ok = True
        clash = lambda yy: any(not (x0 + w < q[0] or q[0] + q[1] < x0 or yy + 2 < q[2] - 9 or q[2] + 2 < yy - 9) for q in placed)
        for _ in range(tries + 1):
            if not clash(y): break
            ny = y + dr * step
            if (lo is not None and ny < lo) or (hi is not None and ny > hi): ok = False; break
            y = ny
        else:
            ok = False
        lb["y0"] = lb["y"]; lb["moved"] = abs(y - lb["y"]) > 0.5; lb["y"] = y; lb["ok"] = ok
        if ok: placed.append((x0, w, y))
    return labels
def _labels_svg(labels, cls="tick"):
    """draw dodged labels (+ a thin leader line to the marker when a label was moved); every label carries a <title> with its full text"""
    out = []
    for lb in labels:
        if not lb.get("ok", True): continue
        if lb.get("moved") and "ay" in lb:
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="var(--muted)" stroke-width=".7" opacity=".55"/>' % (lb["ax"], lb["ay"], lb["x"], lb["y"] - 4))
        out.append('<text x="%.1f" y="%.1f" class="%s" text-anchor="%s"><title>%s</title>%s</text>' % (lb["x"], lb["y"], cls, lb.get("anchor", "middle"), esc(lb.get("title") or lb["text"]), esc(lb["text"])))
    return "".join(out)
def _shape(kind, cx, cy, r, attrs, title=""):
    """marker shapes: circle (default) | diamond | up (triangle up) | down (triangle down)"""
    tl_ = "<title>%s</title>" % esc(title) if title else ""
    if kind == "diamond":
        return '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" %s>%s</polygon>' % (cx, cy - r - 1.5, cx + r + 1.5, cy, cx, cy + r + 1.5, cx - r - 1.5, cy, attrs, tl_)
    if kind == "up":
        return '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" %s>%s</polygon>' % (cx, cy - r - 1.5, cx + r + 1.5, cy + r, cx - r - 1.5, cy + r, attrs, tl_)
    if kind == "down":
        return '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" %s>%s</polygon>' % (cx - r - 1.5, cy - r, cx + r + 1.5, cy - r, cx, cy + r + 1.5, attrs, tl_)
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" %s>%s</circle>' % (cx, cy, r, attrs, tl_)
def legend(x, y, items, maxw=None, rowh=16):
    """horizontal legend row(s) under the axis. items: [(kind, colour, text)], kind dot|small|diamond|up|down|ring|dash|line|band|star.
    Wraps to a new row when maxw is exceeded. Returns (svg, height_px)."""
    out = []; cx0 = x; cy = y; rows = 1
    for kind, col, text in items:
        wd = _tw(text) + 34
        if maxw and cx0 > x and cx0 + wd > maxw: cx0 = x; cy += rowh; rows += 1
        cx = cx0 + 7; my = cy - 4
        if kind == "dot": out.append(_shape("circle", cx, my, 4.5, 'fill="%s"' % col))
        elif kind == "small": out.append(_shape("circle", cx, my, 3, 'fill="%s"' % col))
        elif kind in ("diamond", "up", "down"): out.append(_shape(kind, cx, my, 4, 'fill="%s"' % col))
        elif kind == "ring": out.append(_shape("circle", cx, my, 4, 'fill="none" stroke="%s" stroke-width="2.5"' % col))
        elif kind == "dash": out.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-dasharray="4 3" stroke-width="2"/>' % (cx - 7, cx + 7, my, my, col))
        elif kind == "line": out.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2.5"/>' % (cx - 7, cx + 7, my, my, col))
        elif kind == "band": out.append('<rect x="%.1f" y="%.1f" width="14" height="10" fill="%s" fill-opacity=".25"/>' % (cx - 7, my - 5, col))
        elif kind == "star": out.append('<text x="%.1f" y="%.1f" font-size="14" text-anchor="middle" fill="%s">★</text>' % (cx, my + 5, col))
        out.append('<text x="%.1f" y="%.1f" class="tick">%s</text>' % (cx0 + 18, cy, esc(text)))
        cx0 += wd
    return "".join(out), rows * rowh
def _sub(sub):
    """one-line 'what to look at' subtitle above a chart"""
    return '<p class="note chart-sub"><b>%s</b>%s</p>' % (esc(t("look_at")), esc(sub)) if sub else ""
def _svg_open(w, h):
    return '<svg class="chart" viewBox="0 0 %d %d" role="img" preserveAspectRatio="none" style="width:100%%;height:auto;aspect-ratio:%d/%d">' % (w, h, w, h)
def _pdate(sv):
    s = str(sv).strip()
    for f in ("%d %B %Y", "%Y-%m-%d", "%Y-%m", "%Y"):
        try: return datetime.datetime.strptime(s, f)
        except Exception: pass
    for f, n in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try: return datetime.datetime.strptime(s[:n], f)
        except Exception: pass
    return None
def _time_ticks(t0, t1, maxn=7):
    months = max(1, (t1.year - t0.year) * 12 + t1.month - t0.month)
    step = next((s for s in (1, 2, 3, 6, 12, 24, 60) if months / s <= maxn), 60)
    out = []
    m = datetime.datetime(t0.year, t0.month, 1) if step < 12 else datetime.datetime(t0.year, 1, 1)
    while m <= t1:
        if m >= t0: out.append((m, m.strftime("%Y-%m") if step < 12 else m.strftime("%Y")))
        mo = m.month + step
        m = datetime.datetime(m.year + (mo - 1) // 12, (mo - 1) % 12 + 1, 1)
    return out or [(t0, t0.strftime("%Y-%m")), (t1, t1.strftime("%Y-%m"))]
def _wrap_px(text, maxw, fs=11):
    """greedy wrap by pixel width (CJK breaks anywhere, Latin at spaces)"""
    lines, cur = [], ""
    for tok in re.findall(r"[A-Za-z0-9$.,'\-/%()]+\s*|.", str(text)):
        if cur and _tw(cur + tok, fs) > maxw: lines.append(cur.rstrip()); cur = tok.lstrip()
        else: cur += tok
    if cur.strip(): lines.append(cur.rstrip())
    return lines
def _has(v):
    """True for a usable positive number (None, '', 0, non-numeric -> False)"""
    return num(v) > 0
def _hav_m(lat1, lon1, lat2, lon2):
    R = 6371000.0; p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))
def gmaps_search_url(q):
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(str(q), safe="")
def gmaps_sv_url(lat, lon, q):
    try:
        return "https://www.google.com/maps?q=&layer=c&cbll=%s,%s" % (float(lat), float(lon))
    except (TypeError, ValueError):
        return gmaps_search_url(q)
def _short_money(v):
    return ("$%.2fM" % (v / 1e6)) if abs(v) >= 1e6 else ("$%dk" % round(v / 1e3))
_PRICE_RE = re.compile(r"\$[\d,\.]+\s*[MKmk]?(?![A-Za-z])")
def _event_price(ev):
    """first '$1,170,000' / '$1.1M' / '$900k' in an event text -> number, else None"""
    m = _PRICE_RE.search(str(ev or ""))
    if not m: return None
    s = m.group(0)[1:].strip(); mult = 1
    if s and s[-1] in "MKmk": mult = 1e6 if s[-1] in "Mm" else 1e3; s = s[:-1].strip()
    try: return float(s.replace(",", "").rstrip(".")) * mult
    except ValueError: return None
TL_KINDS = ("sale", "rent", "list", "price_change", "other")
def _tl_kind(r):
    k = str(r.get("kind") or "").strip().lower()
    if k in TL_KINDS: return k
    ev = str(r.get("event", "")).lower()   # no explicit kind: guess from the event text
    if re.search(r"成交|\bsold\b", ev): return "sale"
    if re.search(r"挂牌|\blist(?:ed|ing)?\b", ev): return "list"
    if re.search(r"出租|放租|\brent(?:ed|al)?\b|\bleas", ev): return "rent"
    if re.search(r"调价|降价|涨价|price (?:cut|drop|change|reduc)", ev): return "price_change"
    return "other"

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
def svg_bars(values, labels, fmt=None, w=720, h=200, highlight_last=True, baseline_zero=True, na_text=None):
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
        if v is None:
            if na_text:   # no number for this slot: say why, wrapped, and keep its category label
                ls = _wrap_px(na_text, slot - 16)
                for j, ln in enumerate(ls):
                    out.append('<text x="%.1f" y="%.1f" class="tick" text-anchor="middle">%s</text>' % (pl + slot * i + slot / 2, Y(lo) - 12 - 14 * (len(ls) - 1 - j) - 30, esc(ln)))
                out.append('<text x="%.1f" y="%d" class="tick" text-anchor="middle">%s</text>' % (pl + slot * i + slot / 2, h - 8, esc(labels[i])))
            continue
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
def svg_map(items, w=720, h=360, sub=None):
    pts = [c for c in items if c.get("lon") and c.get("lat")]
    if not pts: return ""
    import math as _m
    lon0 = sum(num(c["lon"]) for c in pts) / len(pts) if not hasattr(svg_map, "subj") else svg_map.subj[0]
    lat0 = sum(num(c["lat"]) for c in pts) / len(pts) if not hasattr(svg_map, "subj") else svg_map.subj[1]
    K = 111320 * _m.cos(_m.radians(lat0))
    xy = [((num(c["lon"]) - lon0) * K, (num(c["lat"]) - lat0) * 111320) for c in pts]
    R = max(1600, max(max(abs(x), abs(y)) for x, y in xy) * 1.1)
    cx, cy = w / 2, h / 2; sc = min(w, h) / 2 / R * 0.95
    body = []
    for r in (500, 1000, 1500):
        if r * sc < min(w, h) / 2:
            body.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" class="grid" stroke-dasharray="3 3"/><text x="%.1f" y="%.1f" class="tick">%d m</text>' % (cx, cy, r * sc, cx + r * sc * 0.72, cy - r * sc * 0.72, r))
    body.append('<text x="%.1f" y="14" class="tick" text-anchor="middle">N ↑</text>' % cx)
    col = VCOL; labels = []; seen_v = []
    for (x, y), c in zip(xy, pts):
        px, py = cx + x * sc, cy - y * sc; v = verdict_of(c)
        if v not in seen_v: seen_v.append(v)
        full = "%s · %s" % (str(c.get("address", "")).title(), money(c.get("price")))
        body.append(_shape("circle", px, py, 6.5, 'fill="%s" fill-opacity=".9" stroke="var(--card)" stroke-width="2"' % col[v], full))
        labels.append({"x": px + 9, "y": py + 4, "text": str(c.get("_letter", "")), "anchor": "start", "fs": 11.5, "ax": px, "ay": py, "title": full})
    dodge(labels, step=12, direction=1, lo=12, hi=h - 6)
    body.append(_labels_svg(labels, "lab halo"))
    body.append('<text x="%.1f" y="%.1f" font-size="24" text-anchor="middle" fill="var(--bad)">★<title>%s</title></text>' % (cx, cy + 9, esc(t("lg_subject"))))
    lg_items = [("star", "var(--bad)", t("lg_subject"))] + [("dot", col[v], vlabel(v)) for v in ("优于", "相当", "逊于", "未知") if v in seen_v] + [("dash", "var(--muted)", "500 / 1,000 / 1,500 m")]
    lg, lh = legend(14, h + 12, lg_items, maxw=w - 14)
    H = h + 8 + lh
    return _sub(sub) + _svg_open(w, H).replace('preserveAspectRatio="none"', 'preserveAspectRatio="xMidYMid meet"') + "".join(body) + lg + '</svg>'
def svg_street_scatter(rows, subj, w=720, h=240, sub=None):
    pts = [(_pdate(r.get("date")), num(r.get("price")), 0 if r.get("strata") else num((r.get("floor_m2") or r.get("land")) if UNIT else r.get("land")), r.get("addr", "")) for r in rows if r.get("price")]
    pts = [p for p in pts if p[0]]
    if len(pts) < 3: return ""
    t0 = min(p[0] for p in pts); t1 = datetime.datetime.today()
    pl, pr, pt, pb = 60, 14, 22, 30
    y0, y1 = min(p[1] for p in pts) * 0.9, max(p[1] for p in pts) * 1.06
    X = lambda d: pl + (w - pl - pr) * ((d - t0).days / max(1, (t1 - t0).days)); Y = lambda v: pt + (h - pt - pb) * (1 - (v - y0) / (y1 - y0))
    body = []
    for k in range(4):
        v = y0 + (y1 - y0) * k / 3
        body.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (pl, w - pr, Y(v), Y(v), pl - 6, Y(v) + 4, _nice(v)))
    _m = datetime.datetime(t0.year, t0.month, 1); _step = 1 if (t1 - t0).days < 400 else (3 if (t1 - t0).days < 1100 else 12)
    while _m <= t1:
        if _m >= t0: body.append('<text x="%.1f" y="%d" class="tick" text-anchor="middle">%s</text>' % (X(_m), h - 8, _m.strftime("%Y-%m") if _step < 12 else _m.strftime("%Y")))
        _mo = _m.month + _step; _m = datetime.datetime(_m.year + (_mo - 1) // 12, (_mo - 1) % 12 + 1, 1)
    lmax = max(p[2] for p in pts) or 1; labels = []
    for d, v, land, addr in pts:
        r = 5 + 9 * (land / lmax) ** 0.5
        full = "%s · %s · %s · %s" % (addr, money(v), d.strftime("%Y-%m-%d"), ("%g m²" % land) if land else "—")
        body.append(_shape("circle", X(d), Y(v), r, 'fill="var(--c1)" fill-opacity=".55" stroke="var(--card)" stroke-width="1.5"', full))
        labels.append({"x": X(d), "y": Y(v) - r - 3, "text": _short_money(v), "anchor": "middle", "dir": -1, "ax": X(d), "ay": Y(v) - r, "title": full})
    dodge(labels, step=12, direction=-1, lo=pt + 4)
    body.append(_labels_svg(labels, "tick"))
    lg_items = [("dot", "var(--c1)", t("lg_sale"))]
    if subj.get("list_price"):
        body.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--bad)" stroke-width="2" stroke-dasharray="5 3"/><text x="%d" y="%.1f" class="lab" text-anchor="end" fill="var(--bad)">%s</text>' % (pl, w - pr, Y(num(subj["list_price"])), Y(num(subj["list_price"])), w - pr, Y(num(subj["list_price"])) - 5, money(subj["list_price"])))
        lg_items.append(("dash", "var(--bad)", t("nav_list")))
    lg, lh = legend(pl, h + 12, lg_items, maxw=w - pr)
    return _sub(sub) + _svg_open(w, h + 8 + lh) + "".join(body) + lg + '</svg>'
def svg_timeline_strip(tl, w=720, sub=None):
    pts = [(_pdate(r.get("date")), r) for r in tl]; pts = sorted([p for p in pts if p[0]], key=lambda p: p[0])
    if len(pts) < 2: return ""
    t0 = pts[0][0]; t1 = pts[-1][0]; span = max(1, (t1 - t0).days)
    pl, pr = 46, 46
    X = lambda d: pl + (w - pl - pr) * ((d - t0).days / span)
    marks, plabs, dlabs, kinds_seen, any_q = [], [], [], [], False
    for i, (d, r) in enumerate(pts):   # layout pass with the axis at y = 0 (labels go up for price, down for date); shifted afterwards
        last = i == len(pts) - 1; ev = str(r.get("event", "")); q = "?" in ev or "待" in ev
        kind = _tl_kind(r)
        price = num(r.get("price")) if r.get("price") not in (None, "") else _event_price(ev)
        price = price if price and price > 0 else None
        if kind not in kinds_seen: kinds_seen.append(kind)
        any_q = any_q or q
        full = "%s · %s%s" % (str(r.get("date")), ev, (" · " + money(price)) if price else "")
        x = X(d)
        marks.append((x, kind, "var(--bad)" if last else ("var(--warn)" if q else "var(--brand)"), q, full))
        if price: plabs.append({"x": x, "y": -16, "text": money(price), "anchor": "middle", "fs": 11.5, "dir": -1, "ax": x, "ay": -8, "title": full})
        dlabs.append({"x": x, "y": 26, "text": str(r.get("date"))[:10], "anchor": "middle", "dir": 1, "ax": x, "ay": 8, "title": full})
    dodge(plabs, step=14, direction=-1, lo=-16 - 14 * 7, tries=8)
    dodge(dlabs, step=12, direction=1, hi=26 + 12 * 7, tries=8)
    AX = int(max(70, 16 - min([lb["y"] for lb in plabs if lb.get("ok")] or [-16]) + 2))
    for lb in plabs + dlabs:
        lb["y"] += AX; lb["ay"] += AX
    body = ['<line x1="%d" x2="%d" y1="%d" y2="%d" class="grid"/>' % (pl, w - pr, AX, AX)]
    for x, kind, fill, q, full in marks:
        body.append(_shape({"rent": "diamond", "list": "up", "price_change": "down"}.get(kind, "circle"), x, AX, 4.5 if kind == "other" else 7, 'fill="%s" stroke="var(--card)" stroke-width="2"' % fill, full))
        if q: body.append('<text x="%.1f" y="%.1f" font-size="10" font-weight="700" text-anchor="middle" fill="#fff" pointer-events="none">?</text>' % (x, AX + 3.5))
    body.append(_labels_svg(plabs, "lab")); body.append(_labels_svg(dlabs, "tick"))
    ly = max([lb["y"] for lb in dlabs if lb.get("ok")] or [AX + 26]) + 26
    names = {"sale": t("tlk_sale"), "rent": t("tlk_rent"), "list": t("tlk_list"), "price_change": t("tlk_pc"), "other": t("tlk_other")}
    shp = {"sale": "dot", "rent": "diamond", "list": "up", "price_change": "down", "other": "small"}
    lg_items = [(shp[k], "var(--brand)", names[k]) for k in TL_KINDS if k in kinds_seen] + [("dot", "var(--bad)", t("tlk_now"))] + ([("dot", "var(--warn)", t("tlk_q"))] if any_q else [])
    lg, lh = legend(pl - 10, ly, lg_items, maxw=w - pr)
    return _sub(sub) + _svg_open(w, ly + lh - 6) + "".join(body) + lg + '</svg>'
def svg_price_steps(hist, rng, w=720, h=200, sub=None):
    """step chart of list-price changes. hist: [{date, price}]; rng: fair range [lo, hi] drawn as a green band"""
    pts = sorted([(_pdate(x.get("date")), num(x.get("price"))) for x in hist if isinstance(x, dict) and x.get("price")], key=lambda p: (p[0] is None, p[0]))
    pts = [p for p in pts if p[0] and p[1] > 0]
    if len(pts) < 2: return ""
    t0 = pts[0][0]; tl_ = pts[-1][0]; span = max(1, (tl_ - t0).days); t1 = tl_ + datetime.timedelta(days=max(14, int(span * 0.12)))
    band = rng if (rng and len(rng) >= 2 and _has(rng[0]) and _has(rng[1])) else None
    ys = [p[1] for p in pts] + ([num(band[0]), num(band[1])] if band else [])
    y0, y1 = min(ys) * 0.95, max(ys) * 1.05
    pl, pr, pt, pb = 60, 16, 26, 30
    X = lambda d: pl + (w - pl - pr) * ((d - t0).days / max(1, (t1 - t0).days)); Y = lambda v: pt + (h - pt - pb) * (1 - (v - y0) / (y1 - y0))
    body = []
    for k in range(4):
        v = y0 + (y1 - y0) * k / 3
        body.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (pl, w - pr, Y(v), Y(v), pl - 6, Y(v) + 4, _nice(v)))
    for d, lab in _time_ticks(t0, t1):
        body.append('<text x="%.1f" y="%d" class="tick" text-anchor="middle">%s</text>' % (X(d), h - 8, lab))
    if band:
        body.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="var(--ok)" opacity=".13"/>' % (pl, Y(num(band[1])), w - pl - pr, max(1, Y(num(band[0])) - Y(num(band[1])))))
    path = "M%.1f,%.1f" % (X(pts[0][0]), Y(pts[0][1]))
    for (d, p), (d2, p2) in zip(pts, pts[1:]):
        path += " H%.1f V%.1f" % (X(d2), Y(p2))
    path += " H%.1f" % X(t1)
    body.append('<path d="%s" fill="none" stroke="var(--c1)" stroke-width="2.5" stroke-linejoin="round"/>' % path)
    labels = []
    for i, (d, p) in enumerate(pts):
        full = "%s · %s" % (d.strftime("%Y-%m-%d"), money(p))
        body.append(_shape("circle", X(d), Y(p), 5, 'fill="var(--c1)" stroke="var(--card)" stroke-width="2"', full))
        labels.append({"x": X(d), "y": Y(p) - 11, "text": money(p), "anchor": "start" if i == 0 else "middle", "fs": 11.5, "dir": -1, "ax": X(d), "ay": Y(p) - 5, "title": full})
    dodge(labels, step=13, direction=-1, lo=12)
    body.append(_labels_svg(labels, "lab halo"))
    lg_items = [("line", "var(--c1)", t("ph_list"))] + ([("band", "var(--ok)", "%s %s – %s" % (t("ph_band"), money(band[0]), money(band[1])))] if band else [])
    lg, lh = legend(pl, h + 12, lg_items, maxw=w - pr)
    return _sub(sub) + _svg_open(w, h + 8 + lh) + "".join(body) + lg + '</svg>'
def svg_scatter(items, subj, rng, w=720, h=260, sub=None):
    xk = "floor_m2" if UNIT else "land_m2"   # x axis: floor area for units, land area for houses
    pts = [c for c in items if c.get(xk) and c.get("price")]
    if not pts: return ""
    xs = [num(c[xk]) for c in pts] + ([num(subj.get(xk))] if subj.get(xk) else [])
    ys = [num(c["price"]) for c in pts] + ([num(subj.get("list_price"))] if subj.get("list_price") else [])
    x0, x1 = min(xs) * 0.92, max(xs) * 1.06; y0, y1 = min(ys) * 0.92, max(ys) * 1.06
    if x1 == x0: x0, x1 = x0 * 0.9, x1 * 1.1
    pl, pr, pt, pb = 60, 14, 22, 30
    X = lambda v: pl + (w - pl - pr) * (v - x0) / (x1 - x0); Y = lambda v: pt + (h - pt - pb) * (1 - (v - y0) / (y1 - y0))
    body = []
    for k in range(4):
        v = y0 + (y1 - y0) * k / 3
        body.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="tick" text-anchor="end">%s</text>' % (pl, w - pr, Y(v), Y(v), pl - 6, Y(v) + 4, _nice(v)))
    for k in range(5):
        v = x0 + (x1 - x0) * k / 4
        body.append('<text x="%.1f" y="%d" class="tick" text-anchor="%s">%.0f m²</text>' % (X(v), h - 8, "start" if k == 0 else ("end" if k == 4 else "middle"), v))
    if rng and rng[0] and rng[1]:
        body.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="var(--ok)" opacity=".13"/>' % (pl, Y(float(rng[1])), w - pl - pr, max(1, Y(float(rng[0])) - Y(float(rng[1])))))
    col = VCOL; labels = []; seen_v = []; any_be = False
    for c in pts:
        v = verdict_of(c); be = c.get("bookend") if v != "未知" else None
        if v not in seen_v: seen_v.append(v)
        any_be = any_be or bool(be)
        px, py = X(num(c[xk])), Y(num(c["price"]))
        full = "%s · %s · %s m²" % (str(c.get("address", "")).title(), money(c.get("price")), c.get(xk))
        body.append(_shape("circle", px, py, 6.5, 'fill="%s" fill-opacity=".9" stroke="%s" stroke-width="%s"' % (col[v], "var(--ink-strong)" if be else "var(--card)", 3 if be else 2), full))
        labels.append({"x": px + 9, "y": py + 4, "text": str(c.get("_letter", "")), "anchor": "start", "fs": 11.5, "dir": 1, "ax": px, "ay": py, "title": full})
    if subj.get(xk) and subj.get("list_price"):
        sx, sy = X(num(subj[xk])), Y(num(subj["list_price"]))
        body.append('<text x="%.1f" y="%.1f" font-size="22" text-anchor="middle" fill="var(--bad)">★<title>%s · %s</title></text>' % (sx, sy + 8, esc(t("lg_subject")), money(subj["list_price"])))
        labels.append({"x": sx, "y": sy - 14, "text": money(subj["list_price"]), "anchor": "middle", "fs": 11.5, "dir": -1, "ax": sx, "ay": sy - 8, "title": "%s · %s" % (t("lg_subject"), money(subj["list_price"]))})
    dodge(labels, step=12, direction=1, lo=pt - 6, hi=h - pb - 2)
    body.append(_labels_svg(labels, "lab halo"))
    lg_items = [("dot", col[v], vlabel(v)) for v in ("优于", "相当", "逊于", "未知") if v in seen_v]
    if any_be: lg_items.append(("ring", "var(--ink-strong)", t("lg_bookend")))
    if subj.get(xk) and subj.get("list_price"): lg_items.append(("star", "var(--bad)", t("lg_subject")))
    if rng and rng[0] and rng[1]: lg_items.append(("band", "var(--ok)", t("nav_range")))
    lg, lh = legend(pl, h + 12, lg_items, maxw=w - pr)
    return _sub(sub) + _svg_open(w, h + 8 + lh) + "".join(body) + lg + '</svg>'
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

# ---------------------------------------------------------------- comparable links, same-building rule, real map
_ST = {"CL": "close", "CRES": "crescent", "AVE": "avenue", "RD": "road", "DR": "drive", "PL": "place", "ST": "street", "CCT": "circuit", "PDE": "parade", "CT": "court", "BVD": "boulevard", "GR": "grove", "TCE": "terrace", "LANE": "lane", "WAY": "way", "HWY": "highway", "ESP": "esplanade", "CRT": "court"}
_ADDR_TAIL = re.compile(r",\s*([A-Za-z' ]+?)\s+(NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s+(\d{4})\s*$", re.I)
def _safe_url(u):
    u = str(u or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else ""
def comp_url(c, cp, subj):
    """Link for one comparable. An explicit items[].url wins; otherwise comps.profile_url_pattern ({slug}) is filled from the
    comparable's address plus the subject's suburb / state / postcode (a comp address that carries its own ', Suburb' or full tail uses that)."""
    u = _safe_url(c.get("url"))
    if u: return u
    pat = _safe_url(cp.get("profile_url_pattern"))
    if not pat or "{slug}" not in pat: return ""
    addr = re.sub(r"\s*[\(（][^\)）]*[\)）]", "", str(c.get("address", ""))).strip()
    stail = _ADDR_TAIL.search(str(subj.get("address", "")))
    m = _ADDR_TAIL.search(addr)
    if m: street, sub, stt, pc = addr[:m.start()], m.group(1), m.group(2), m.group(3)
    else:
        street, _, sub = addr.partition(",")
        sub = sub.strip()
        if not stail: return ""
        stt, pc = stail.group(2), stail.group(3)
        if not sub: sub = stail.group(1)
    words = street.replace(",", " ").split()
    if not words: return ""
    if words[-1].upper() in _ST: words[-1] = _ST[words[-1].upper()]
    slug = "-".join(w.lower() for w in words + sub.split() + [stt, pc])
    slug = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9-]", "", slug.replace("/", "-"))).strip("-")
    return pat.replace("{slug}", slug) if slug else ""
def addr_html(c, url=""):
    a = esc(str(c.get("address", "")).title())
    if not url: return a
    return '<a href="%s" target="_blank" rel="noopener" title="%s">%s ↗</a>' % (esc(url), esc(t("open_profile")), a)
def same_bldg(subj, items):
    """True when every comparable with coordinates is within 50 m of the subject, or they all share one coordinate (same building): no map is drawn."""
    cc = [(num(c["lat"]), num(c["lon"])) for c in items if c.get("lat") and c.get("lon")]
    if not cc: return False
    skip = False
    if subj.get("lat") not in (None, "") and subj.get("lon") not in (None, ""):
        skip = all(_hav_m(num(subj["lat"]), num(subj["lon"]), la, lo) <= 50 for la, lo in cc)
    if not skip and len(cc) >= 2: skip = len({(round(la, 6), round(lo, 6)) for la, lo in cc}) == 1
    return skip
def _ring_pts(ring):
    out = []
    for p in ring or []:
        try: out.append([float(p[0]), float(p[1])])
        except (TypeError, ValueError, IndexError, KeyError): continue
    return out if len(out) >= 3 else []
def _jsdump(o): return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")
LEAFLET = {"js": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js", "css": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
           "js_sri": "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=", "css_sri": "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="}
_LEAFLET_JS = r"""(function(){
var P=__P__,S=__S__,R=__R__,SN=__SN__,JS=__JS__,CSS=__CSS__,JSI=__JSI__,CSSI=__CSSI__;
var box=document.getElementById("cmap-real"),el=document.getElementById("cmap"),fb=document.getElementById("cmap-fallback"),nt=document.getElementById("cmap-fail");
var drawn=false,m=null,ok=0,bad=0;
function fail(){if(m){try{m.remove()}catch(e){}m=null}drawn=false;box.style.display="none";fb.style.display="block";nt.style.display="block"}
function show(){box.style.display="block";return el.offsetWidth>0}
function draw(){
 if(drawn)return;
 try{
  m=L.map(el,{scrollWheelZoom:false});
  var tl=L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; OpenStreetMap contributors"}).addTo(m);
  tl.on("tileload",function(){ok++}).on("tileerror",function(){bad++;if(!ok&&bad>=4)fail()});
  var g=L.featureGroup();
  if(R.length){L.polygon(R.map(function(q){return [q[1],q[0]]}),{color:"#1f8a56",weight:2,fillOpacity:.25}).addTo(g)}
  L.marker(S,{icon:L.divIcon({className:"cm-subj",html:"\u2605",iconSize:[26,26],iconAnchor:[13,13]}),zIndexOffset:1000}).addTo(g).bindTooltip(SN);
  P.forEach(function(c){L.marker([c.lat,c.lon],{icon:L.divIcon({className:"cm-"+c.v,html:c.l,iconSize:[22,22],iconAnchor:[11,11]})}).addTo(g).bindTooltip(c.a+" \u00b7 "+c.p).on("click",function(){
   if(c.u){window.open(c.u,"_blank","noopener")}else{var a=document.getElementById("comp-"+c.l);if(a){a.open=true;a.scrollIntoView({block:"center"})}}})});
  g.addTo(m);m.fitBounds(g.getBounds().pad(.15),{maxZoom:17});
  drawn=true;fb.style.display="none";nt.style.display="none";
  setTimeout(function(){if(drawn&&!ok)fail()},10000);
 }catch(e){fail()}
}
function start(){
 if(drawn||!window.L)return;
 if(show()){draw();return}
 box.style.display="none";
 var f=function(){if(show()){document.removeEventListener("toggle",f,true);draw()}else{box.style.display="none"}};
 document.addEventListener("toggle",f,true);
}
if(window.L){start()}else{
 var ln=document.createElement("link");ln.rel="stylesheet";ln.href=CSS;ln.integrity=CSSI;ln.crossOrigin="";document.head.appendChild(ln);
 var sc=document.createElement("script");sc.src=JS;sc.integrity=JSI;sc.crossOrigin="";sc.onload=start;sc.onerror=fail;document.head.appendChild(sc);
 setTimeout(function(){if(!window.L)fail()},8000);
}
})();"""
def leaflet_block(pts, ring, subj, fallback_html):
    """OpenStreetMap + Leaflet map with the self-drawn svg_map as fallback. The Leaflet CSS/JS tags exist only inside this block, so they are
    emitted only when a map is actually drawn; the script injects them, then draws once the section is visible. Offline / CDN failure ->
    the svg stays and a one-line note (map_failed) plus a Google Maps link shows."""
    gm = _safe_url(subj.get("map_url")) or gmaps_search_url(subj.get("address", ""))
    js = (_LEAFLET_JS.replace("__P__", _jsdump(pts)).replace("__S__", _jsdump([num(subj["lat"]), num(subj["lon"])])).replace("__R__", _jsdump(ring))
          .replace("__SN__", _jsdump(esc(subj.get("address", "")))).replace("__JS__", _jsdump(LEAFLET["js"])).replace("__CSS__", _jsdump(LEAFLET["css"]))
          .replace("__JSI__", _jsdump(LEAFLET["js_sri"])).replace("__CSSI__", _jsdump(LEAFLET["css_sri"])))
    return ('<div id="cmap-real" style="display:none"><h3>%s</h3><div id="cmap" class="cmap"></div><p class="note">%s</p></div>'
            '<p class="note" id="cmap-fail" style="display:none"><span class="warn">%s</span> <a href="%s" target="_blank" rel="noopener">%s</a></p>'
            '<div id="cmap-fallback">%s</div><script>%s</script>') % (
            t("map_real_h"), t("map_attrib"), t("map_failed"), esc(gm), t("map_gmaps"), fallback_html, js)

# ---------------------------------------------------------------- standard figures (the report is consistent because this list is)
# (id, section, required data.json fields, applies to house|unit|both, (zh name, en name), optional applicability test)
# fields grammar: a.b.c = non-empty value; a.b[x,y]>=N = at least N list items that all carry x and y; @a.b = svg text or an existing file path;
#                 '+' = all of, '|' = any of
FIGURES = [
 ("hero_gallery", "s0", "photos.images", "both", ("首图相册", "Hero photo gallery"), None),
 ("source_chips", "s0", "photos.sources", "both", ("来源核对标签", "Source-check chips"), None),
 ("status_cards", "s0", "summary.cards|status_cards", "both", ("五张状态卡", "Five status cards"), None),
 ("offer_tiles", "s0", "summary.offer.walk_away", "both", ("出价三格", "Offer tiles"), None),
 ("timeline_strip", "s2", "timeline[date]>=2", "both", ("时间线条带", "Timeline strip"), None),
 ("dom_bars", "s2", "dom.months_approx+dom.suburb_median_dom", "both", ("在市天数对比条", "Days-on-market bars"), None),
 ("price_steps", "s2", "dom.price_history[date,price]>=2", "both", ("挂牌价阶梯图", "List-price step chart"), None),
 ("price_line", "s2", "summary.range+summary.offer.walk_away", "both", ("出价价格轴", "Offer price axis"), None),
 ("tier_table", "s2", "summary.offer.walk_away", "both", ("出价三档表", "Offer tier table"), None),
 ("price_ruler", "s2", "ruler.prices", "both", ("成交价标尺", "Sale-price ruler"), None),
 ("hazard_tiles", "s3", "hazards", "both", ("风险方块", "Hazard tiles"), None),
 ("coverage_bar", "s3", "hazards", "both", ("核查覆盖条", "Coverage bar"), None),
 ("site_map", "s4", "@land.site_svg", "house", ("地块图", "Site map"), None),
 ("ground_profile", "s4", "@land.profile_svg", "house", ("地形剖面图", "Terrain profile"), None),
 ("land_value_bars", "s4", "subject.land_value.history", "both", ("地价历史柱图", "Land-value bars"), None),
 ("street_scatter", "s4", "land.street_sales[date,price,land]>=3", "house", ("同街成交散点", "Same-street sales scatter"), None),
 ("street_table", "s4", "land.street_sales[addr,price]", "house", ("同街成交表", "Same-street sales table"), None),
 ("stack_chart", "s4", "@land.stack_svg", "unit", ("同竖列 × 楼层图", "Stack × floor chart"), None),
 ("building_chart", "s4", "@land.building_svg", "unit", ("户型 × 成交日图", "Layout × sale-date chart"), None),
 ("building_sales", "s4", "land.building_sales[price,date]", "unit", ("楼内成交表", "Building sales table"), None),
 ("comp_matrix", "s5", "comps.items[address,price]", "both", ("可比一览表", "Comparables matrix"), None),
 ("comp_scatter", "s5", "comps.items[land_m2,price]", "house", ("可比散点(土地 × 价)", "Comparables scatter (land × price)"), None),
 ("comp_scatter", "s5", "comps.items[floor_m2,price]", "unit", ("可比散点(面积 × 价)", "Comparables scatter (floor × price)"), None),
 ("comp_map", "s5", "comps.items[lon,lat]+subject.lon+subject.lat", "both", ("可比地图", "Comparables map"),
  lambda d: not same_bldg(d.get("subject") or {}, (d.get("comps") or {}).get("items") or [])),
 ("comp_cards", "s5", "comps.items[address,price]", "both", ("可比卡片", "Comparable cards"), None),
 ("mortgage_bars", "s5", "subject.list_price|summary.offer.walk_away", "both", ("月供对比柱", "Mortgage bars"), None),
 ("future_chips", "s6", "future", "both", ("未来规划标签", "Future-plan chips"), None),
 ("vacancy_line", "s7", "market.vacancy.rows", "both", ("空置率折线", "Vacancy line"), None),
 ("stock_lines", "s7", "market.som.rows", "both", ("在售量折线", "Stock-on-market lines"), None),
 ("growth_bars", "s7", "market.growth.rows", "both", ("增长率条", "Growth bars"), None),
 ("yearly_line", "s7", "market.yearly", "both", ("年度中位价折线", "Yearly median line"), None),
 ("asking_lines", "s7", "market.ask", "both", ("挂牌均价折线", "Asking-price lines"), None),
 ("count_progress", "foot", "hazards", "both", ("桌面 / 现场进度条", "Desktop vs field bar"), None),
]
def _fig_term(d, term):
    term = term.strip()
    if term.startswith("@"):
        v = _dig(d, term[1:])
        if not v: return False
        if str(v).lstrip().startswith("<svg"): return True
        fp = str(v) if os.path.isabs(str(v)) else os.path.join(os.path.dirname(os.path.abspath(d.get("_path") or ".")), str(v))
        return os.path.exists(fp)
    m = re.fullmatch(r"([A-Za-z_.]+)(?:\[([^\]]+)\])?(?:>=(\d+))?", term)
    cur = _dig(d, m.group(1))
    if cur in (None, "", [], {}): return False
    if m.group(2) is None: return True
    if not isinstance(cur, list): return False
    need = [x.strip() for x in m.group(2).split(",")]
    return sum(1 for it in cur if isinstance(it, dict) and all(it.get(n) not in (None, "", [], {}) for n in need)) >= int(m.group(3) or 1)
def _dig(d, path):
    cur = d
    for k in path.split("."):
        cur = cur.get(k) if isinstance(cur, dict) else None
        if cur is None: return None
    return cur
def figures_check(d):
    """[(id, section, fields, ok, name)] for the standard figures that apply to this data.json (house or unit); ok = the data the figure needs is present."""
    unit = is_unit(d); out = []
    for fid, sec_, spec, scope, names, applies in FIGURES:
        if scope != "both" and (scope == "unit") != unit: continue
        if applies is not None and not applies(d): continue
        ok = any(all(_fig_term(d, term) for term in alt.split("+")) for alt in spec.split("|"))
        out.append((fid, sec_, spec, ok, names[0 if LANG == "zh" else 1]))
    return out
def fig_warning(r):
    return "standard figure %s (%s, %s) not produced: needs %s" % (r[0], r[1], r[4], r[2])

def comp_card(c, subj, warnings, ctx="", url=""):
    v = verdict_of(c); cls = VCLS[v]
    _a = re.sub(r"\s*[\(（][^\)）]*[\)）]", "", str(c.get("address", ""))).strip()
    if c.get("lat") not in (None, "") and c.get("lon") not in (None, ""): _mq = "%s,%s" % (c["lat"], c["lon"])
    else: _mq = ("%s, %s" % (_a, ctx)) if (ctx and "," not in _a) else _a
    ml = ('<p class="mapl"><a href="%s" target="_blank" rel="noopener">%s</a></p>' % (esc(gmaps_search_url(_mq)), t("map_link"))) if _mq else ""
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
    thumb = ('<img class="cthumb" src="%s" alt="" referrerpolicy="no-referrer" loading="lazy">' % esc(c["thumb"])) if _safe_url(c.get("thumb")) else ""
    if thumb and url: thumb = '<a href="%s" target="_blank" rel="noopener" title="%s">%s</a>' % (esc(url), esc(t("open_profile")), thumb)
    head = '%s%s<b>%s</b> · %s · <b>%s</b><span class="sdots">%s</span><span class="cmp">%s %d/8 <span class="cdots">%s</span></span><span class="dist">%s</span>' % (
        tags, thumb, addr_html(c, url), esc(c.get("date", "")), money(c.get("price")), sdots,
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
        return '<details class="comp %s" id="comp-%s"%s><summary>%s</summary>%s%s</details>' % (cls, c.get("_letter", ""), " open" if open_ else "", head, body, ml)
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
    return '<details class="comp %s" id="comp-%s"%s><summary>%s</summary>%s%s</details>' % (cls, c.get("_letter", ""), " open" if open_ else "", head, body, ml)

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
    _chips = []
    for s_ in (ph0.get("sources") or []):
        if not isinstance(s_, dict) or not (s_.get("name") or s_.get("url")): continue
        _ok = s_.get("ok") is not False
        _u = str(s_.get("url") or ""); _nm = esc(s_.get("name") or _u)
        _in = ('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(_u), _nm)) if _u.lower().startswith(("http://", "https://")) else _nm
        _chips.append('<span class="chip %s" title="%s">%s <b>%s</b></span>' % ("ok" if _ok else "bad", esc(s_.get("crosscheck", "")), _in, "✓" if _ok else "✗"))
    if _chips: gal += '<div class="srcchips"><span class="lbl">%s</span>%s</div>' % (esc(t("src_chips")), "".join(_chips))
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
    _addr_full = subj.get("address", ""); maplinks = ""
    if _addr_full or (subj.get("lat") not in (None, "") and subj.get("lon") not in (None, "")):
        _mu = subj.get("map_url") or gmaps_search_url(_addr_full)
        _su = subj.get("streetview_url") or ph0.get("streetview_url") or gmaps_sv_url(subj.get("lat"), subj.get("lon"), _addr_full)
        maplinks = '<span class="maplinks"><a href="%s" target="_blank" rel="noopener">%s</a><a href="%s" target="_blank" rel="noopener">%s</a></span>' % (esc(_mu), t("map_link"), esc(_su), t("sv_link"))
    panel = '<div class="addr">%s%s</div><div class="src">%s</div><div class="facts">%s</div><dl class="kv2">%s</dl>' % (
        esc(addr_parts[0]), maplinks, esc(" · ".join(x for x in [addr_parts[1] if len(addr_parts) > 1 else "", subj.get("lot_dp", ""), subj.get("dwelling", "")] if x)), facts, kv2)
    hero = '<section class="hero"><div class="gallery">%s</div><div class="panel">%s</div></section>' % (gal, panel)
    cards = ""
    for c in scards:
        cards += '<div class="card"><div class="k">%s</div><div class="v %s">%s</div><div class="note">%s</div>%s</div>' % (
            esc(c.get("label")), cls_of(c.get("status")), esc(c.get("value")), esc(c.get("note", "")), nextcell(c.get("next", "")))
    offer_html = ""
    if offer:
        _fok = _has(offer.get("first"))   # first offer is optional: without it the tile says it is set after talking to the agent
        offer_html = '<div class="offer"><div><div class="k">%s</div><div class="n%s">%s</div></div><div><div class="k">%s</div><div class="n">%s</div></div><div><div class="k">%s</div><div class="n">%s</div><div class="note">%s</div></div></div>' % (
            t("offer_first"), "" if _fok else " tbd", money(offer.get("first")) if _fok else esc(t("offer_tbd")), t("offer_walk"), money(offer.get("walk_away")),
            t("offer_conf"), esc(offer.get("confidence", "—")), esc(offer.get("confidence_note", "")))
        offer_html += '<div class="offerdisc">%s</div>' % t("offer_disclaimer")
    summary = '%s<div class="verdict"><b>%s:</b>%s</div><div class="cards">%s</div>%s<p class="maxrisk"><b>%s:</b>%s</p><p class="note disclaimer">%s</p>' % (
        hero, t("one_line"), esc(summ.get("verdict_line", "")), cards, offer_html, t("max_risk"), esc(summ.get("max_risk", "")), t("disclaimer", date=date))

    S = []
    # ---- 1 overview
    _facts = []
    for row in subj.get("facts", []):
        if isinstance(row, (list, tuple)) and len(row) >= 2 and not dup_fact(row[0]): _facts.append((row[0], row[1]))
    ph = d.get("photos", {})
    if ph.get("material_from_photos"):   # one facts row instead of a separate paragraph; a duplicated label prefix is stripped
        _mfp = str(ph["material_from_photos"]).strip()
        for _lab in T["material_from_photo"]:
            if _mfp.lower().startswith(_lab.lower()):
                _mfp = re.sub(r"^[\s:：,，\-–—]+", "", _mfp[len(_lab):]); break
        if _mfp: _facts.append((t("material_from_photo"), _mfp))
    kv = "".join('<div%s><b>%s</b>%s</div>' % (' class="wide"' if len(str(v)) > 90 else "", esc(k), esc(v)) for k, v in _facts)   # long values span the whole row
    S.append(sec("s1", '<div class="kv">%s</div>' % kv))

    # ---- 2 timeline + ruler
    tl = d.get("timeline", [])
    _strip = svg_timeline_strip(tl, sub=t("sub_tl"))
    tlh = '<h3 style="margin-top:0">%s</h3>%s<p class="note">%s</p><ol class="tl">%s</ol>' % (t("tl_h"), _strip, t("tl_strip_note") if _strip else "",
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
    _phs = svg_price_steps(dom.get("price_history") or [], summ.get("range"), sub=t("sub_steps"))
    if _phs: domh += "<h3>%s</h3>%s" % (t("ph_h"), _phs)
    if dom.get("price_history_status", "unverified") != "verified":
        domh += '<p><span class="warn">%s</span></p>%s' % (t("dom_unverified"), paid("price-history", t("dom_h")))
    # price narrative: one axis
    _of = summ.get("offer", {}); _rng = summ.get("range") or [None, None]; _avm = summ.get("avm_range") or []
    _pts = [(t("nav_list"), subj.get("list_price"), "list"), (t("offer_first"), _of.get("first"), "first"), (t("offer_walk"), _of.get("walk_away"), "walk")]
    for _i, _c in enumerate(d.get("comps", {}).get("items", [])):
        if _c.get("price"): _pts.append((letter(_i), num(_c["price"]), "comp"))
    _bands = [(_rng[0], _rng[1], "range")] + ([(_avm[0], _avm[-1], "avm")] if len(_avm) >= 2 else [])
    pline = svg_priceline(_pts, _bands)
    tth = tt("tier_th"); _fok2 = _has(_of.get("first"))
    tiers = '<h3>%s</h3><table class="tiers"><tr>%s</tr><tr><td>%s</td><td%s><b>%s</b></td><td>%s</td></tr><tr><td>%s</td><td><b>%s – %s</b></td><td>%s</td></tr><tr><td>%s</td><td><b>%s</b></td><td>%s</td></tr></table>' % (
        t("tiers_h"), "".join("<th>%s</th>" % x for x in tth),
        t("tier_first"), "" if _fok2 else ' class="tbd"', money(_of.get("first")) if _fok2 else esc(t("offer_tbd")), esc(d.get("pricing", {}).get("first_offer_text", "")),
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
        rh += "<h3>%s</h3><p class=\"note\">%s</p><p>%s</p><div class=\"ruler\">%s%s<div class=\"me\" style=\"left:%.1f%%\"></div><div class=\"lab me-lab\" style=\"left:%.1f%%\">%s</div>%s</div><p class=\"note\">%s</p>" % (
            t("range_how"), esc(summ.get("range_note", "")),
            t("ruler_lead", window=esc(rl.get("window_label", "")), n=rl.get("n", len(prices)), median=money(rl.get("median") or statistics.median(prices)), list=money(L)),
            band, dots + ticks + more, x(L), max(15, min(85, x(L))), t("ruler_me", list=money(L), pct=pct), labs, t("ruler_note2") + tick_note)
    S.append(sec("s2", '<p class="ai-note">%s</p>' % esc(t("ai_note")) + tlh + domh + rh))

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
        if not os.path.exists(fp): return '<p class="na">[%s missing: %s]</p>' % (key, esc(p))
        with open(fp, encoding="utf-8") as fh: return fh.read()
    lkv = "".join("<div><b>%s</b>%s</div>" % (esc(k), esc(v)) for k, v in ld.get("facts", []))
    lvh = ""
    lvhist = (subj.get("land_value") or {}).get("history") or {}
    if lvhist:
        ys = sorted(lvhist)
        _yrs = sorted(lvhist.keys()); lvh = "<h3>%s</h3>%s%s<p class=\"note\">%s</p>" % (t("lv_h"), svg_bars([num(lvhist[y]) for y in _yrs], [str(y) for y in _yrs], fmt=money, h=180), tbl_src("<table><tr>%s</tr><tr>%s</tr></table>" % ("".join("<th>%s</th>" % esc(y) for y in _yrs), "".join("<td>%s</td>" % money(lvhist[y]) for y in _yrs))), esc(ld.get("lv_note", "")))
    ss = ld.get("street_sales", [])
    def _street_table(rows_):
        def _land(r):
            if r.get("strata"): return '<td title="%s"></td>' % esc(t("strata_tip"))   # strata lot: no separate land area
            return "<td>%s m²</td>" % esc((r.get("floor_m2") or r.get("land")) if UNIT else r.get("land"))
        return "<h3>%s</h3><table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>%s</table>%s" % (t("street_sales_h"),
              "Address", "Price", "Date", "m²" if UNIT else "Land",
              "".join("<tr><td>%s</td><td>%s</td><td>%s</td>%s</tr>" % (esc(r.get("addr")), money(r.get("price")), esc(r.get("date")), _land(r)) for r in rows_),
              ('<p class="note">%s</p>' % t("strata_note")) if any(r.get("strata") for r in rows_) else "")
    if UNIT:
        # unit mode: no site / profile / street-scatter figures; stack x floor and layout x date charts + the unfiltered building sales
        _bs = sorted([r for r in (ld.get("building_sales") or []) if isinstance(r, dict)], key=lambda r: _pdate(r.get("date")) or datetime.datetime.min, reverse=True)
        if _bs:
            _bth = tt("bsales_th")
            _lay = lambda r: "·".join(str(r.get(k_)) if r.get(k_) not in (None, "") else "—" for k_ in ("beds", "baths", "cars"))
            ssh = '<h3>%s</h3><div class="tw"><table class="bs"><tr>%s</tr>%s</table></div>' % (t("bsales_h"), "".join("<th>%s</th>" % esc(x) for x in _bth),
                  "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                      esc(r.get("unit")), esc(_lay(r)), esc(("%g" % num(r["floor_m2"])) if _has(r.get("floor_m2")) else "—"), money(r.get("price")), esc(r.get("date")), esc(r.get("source", ""))) for r in _bs))
        else:
            ssh = _street_table(ss) if ss else ""   # older data without building_sales keeps the street-sales table (no scatter)
        _fa = read_fig("stack_svg"); _fb = read_fig("building_svg")
        figs = (("<h3>%s</h3>%s" % (t("stack_h"), _fa)) if _fa else "") + (("<h3>%s</h3>%s" % (t("bldg_h"), _fb)) if _fb else "")
        if ld.get("building_read"): figs += "<p>%s</p>" % esc(ld["building_read"])
        top = ('<div class="two"><div><div class="kv" style="grid-template-columns:1fr">%s</div></div><div>%s</div></div>' % (lkv, lvh)) if lvh else (('<div class="kv">%s</div>' % lkv) if lkv else "")
        land_html = top + figs + ssh
    else:
        _sc = svg_street_scatter(ss, subj, sub=t("sub_street")); ssh = ("<h3>%s</h3>%s" % (t("street_scatter_h"), _sc)) if _sc else ""
        if ss: ssh += _street_table(ss)
        land_html = '<div class="two"><div>%s</div><div><div class="kv" style="grid-template-columns:1fr">%s</div>%s</div></div><h3>%s</h3>%s%s' % (
        read_fig("site_svg"), lkv, lvh, t("profile_h"), ((("<p class=\"note\">%s</p>" % t("profile_flat", s=ld["profile_flat"].get("street", "—"), r=ld["profile_flat"].get("rear", "—"), f=ld["profile_flat"].get("fall", 0))) if isinstance(ld.get("profile_flat"), dict) else "") + read_fig("profile_svg")), ssh)
    S.append(sec("s4", land_html))

    # ---- 5 comps
    for _i, _c in enumerate(d.get("comps", {}).get("items", [])): _c["_letter"] = letter(_i)
    cp = d.get("comps", {}); items = cp.get("items", [])
    csubj = cp.get("subject") or {"land_m2": subj.get("land_m2")}
    if UNIT and not csubj.get("floor_m2"): csubj = dict(csubj, floor_m2=subj.get("floor_m2"))
    _ctx = (re.split(r",\s*", subj.get("address", ""), maxsplit=1) + [""])[1]   # suburb / state tail of the subject address, for comp map links
    cards_html = "".join(comp_card(c, csubj, warnings, ctx=_ctx, url=comp_url(c, cp, subj)) for c in items)
    plv = sorted(num(c["p_lv"]) for c in items if c.get("p_lv"))
    svg_map.subj = (subj.get("lon"), subj.get("lat")) if subj.get("lon") and subj.get("lat") else None
    if not svg_map.subj: delattr(svg_map, "subj")
    mth = tt("matrix_th")
    _sd = lambda c, k: {1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get(k))]
    if UNIT:   # floor m² / level (+ level·aspect·view score) / cars (+ area & cars score)
        _rows = "".join('<tr class="%s"><td><a href="#comp-%s" class="letter">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><i class="sd %s"></i> %s</td><td><i class="sd %s"></i> %s</td><td><i class="sd %s"></i></td><td>%d/8</td></tr>' % (
            VCLS[verdict_of(c)], c.get("_letter"), c.get("_letter"), addr_html(c, comp_url(c, cp, subj)), esc(str(c.get("date", ""))), money(c.get("price")), esc(c.get("floor_m2") or "—"), ("%s m" % c.get("dist_m")) if c.get("dist_m") is not None else "—",
            _sd(c, "slope"), esc(c.get("level") if c.get("level") not in (None, "") else "—"), _sd(c, "land"), esc(c.get("cars") if c.get("cars") not in (None, "") else "—"), _sd(c, "condition"), completeness(c)) for c in cp.get("items", []))
    else:
        _rows = None
    matrix = '<h3 style="margin-top:0">%s</h3><div class="tw"><table class="mx"><tr>%s</tr>%s</table></div>' % (t("matrix_h"), "".join("<th>%s</th>" % x for x in mth), "".join(
        '<tr class="%s"><td><a href="#comp-%s" class="letter">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><i class="sd %s"></i></td><td><i class="sd %s"></i></td><td><i class="sd %s"></i></td><td>%d/8</td></tr>' % (
            VCLS[verdict_of(c)], c.get("_letter"), c.get("_letter"), addr_html(c, comp_url(c, cp, subj)), esc(str(c.get("date", ""))), money(c.get("price")), c.get("p_lv") or "—", ("%s m" % c.get("dist_m")) if c.get("dist_m") is not None else "—",
            {1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get("land"))], {1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get("slope"))], {1: "up", 0: "eq", -1: "dn", None: "na"}[score_val(c.get("scores", {}).get("condition"))], completeness(c)) for c in cp.get("items", [])))
    if _rows is not None:
        matrix = '<h3 style="margin-top:0">%s</h3><div class="tw"><table class="mx"><tr>%s</tr>%s</table></div>' % (t("matrix_h"), "".join("<th>%s</th>" % x for x in mth), _rows)
    # comparables map: skipped when every comp with coordinates is within 50 m of the subject, or they all share one coordinate (same building).
    # Otherwise a real OpenStreetMap / Leaflet map (subject star, lot boundary, lettered comps coloured by verdict, click = profile link);
    # the self-drawn svg_map is the fallback when offline or the CDN fails (then map_failed + a Google Maps link show).
    _skip_map = same_bldg(subj, cp.get("items", []))
    mp = ""
    if not _skip_map:
        _svg = svg_map(cp.get("items", []), sub=t("sub_map")); _fb = ("<h3>%s</h3>%s" % (t("map_h"), _svg)) if _svg else ""
        _pts = [{"l": c.get("_letter"), "lon": num(c["lon"]), "lat": num(c["lat"]), "a": esc(str(c.get("address", "")).title()), "p": money(c.get("price")), "v": VCLS[verdict_of(c)], "u": comp_url(c, cp, subj)}
                for c in cp.get("items", []) if c.get("lon") and c.get("lat")]
        if _pts and subj.get("lon") not in (None, "") and subj.get("lat") not in (None, ""):
            mp = leaflet_block(_pts, _ring_pts(d.get("land", {}).get("ring")), subj, _fb)
        else:
            mp = _fb
    scat = svg_scatter(cp.get("items", []), subj, summ.get("range"), sub=t("sub_scatter"))
    scat_blk = ("<h3>%s</h3>%s<p class=\"note\">%s</p>" % (t("scatter_h"), scat, t("scatter_note"))) if scat else ""
    if _skip_map:
        scat = matrix + scat_blk + '<p class="note">%s</p>' % t("map_same_bldg")
    else:
        scat = matrix + '<div class="two"><div>' + scat_blk + "</div><div>" + mp + "</div></div>"
    plvh = ""
    if plv and not UNIT:   # P/LV cross-check is a land-value test; meaningless for strata units
        plvh = "<h3>%s</h3><p>%s</p>" % (t("plv_h"), esc(cp.get("p_lv_note", "")) or ("%d comps, P/LV %.2f–%.2f, median %.2f" % (len(plv), plv[0], plv[-1], statistics.median(plv))))
    pr = d.get("pricing", {}); prh = "<h3>%s</h3><p>%s</p>" % (t("pricing_h"), esc(pr.get("method_note", "")))
    _bku = pr.get("bookend_upper_text") or pr.get("upper") or ""   # legacy aliases: pricing.upper / pricing.lower (bookend texts only)
    _bkl = pr.get("bookend_lower_text") or pr.get("lower") or ""
    if _bku or _bkl:
        prh += "<ul><li><b>%s:</b>%s</li><li><b>%s:</b>%s</li></ul>" % (t("bk_upper"), esc(_bku), t("bk_lower"), esc(_bkl))
    if pr.get("widen_reason"):
        prh += '<p class="note"><b>%s</b>%s</p>' % (esc(t("widen_pref")), esc(pr["widen_reason"]))
    mg = pr.get("mortgage") or {}
    _rate = float(mg.get("rate", 0.0615))
    if _rate > 1:
        print("mortgage.rate looks like a percent; using %g" % (_rate / 100), file=sys.stderr); _rate = _rate / 100
    _lvr = float(mg.get("lvr", 0.8))
    if _lvr > 1:
        print("mortgage.lvr looks like a percent; using %g" % (_lvr / 100), file=sys.stderr); _lvr = _lvr / 100
    _years = int(mg.get("years", 30)); _step = float(mg.get("step", 50000)); _lvr_s = "%g" % round(_lvr * 100, 2)
    _mr = _rate / 12; _mn = _years * 12
    _pay = lambda P: ((P * _mr / (1 - (1 + _mr) ** (-_mn))) if _mr > 0 else P / _mn) if P else None   # repayment on the loan P (= price x LVR)
    _o2 = summ.get("offer", {})
    _three = [(t("offer_first"), _o2.get("first")), (t("mort_list"), subj.get("list_price")), (t("offer_walk"), _o2.get("walk_away"))]
    _three = [(k, _pay(float(v) * _lvr) if _has(v) else None) for k, v in _three]
    _three = [(k, v) for i, (k, v) in enumerate(_three) if i == 0 or v is not None]   # a missing first offer stays as a "set later" slot; other missing prices are dropped
    if any(v is not None for k, v in _three):
        prh += "<h3>%s</h3>%s" % (t("mort_h", lvr=_lvr_s), svg_bars([v for k, v in _three], [k for k, v in _three], fmt=(lambda v: money(v) + ("/月" if LANG == "zh" else "/mo")), h=170, highlight_last=False, na_text=t("offer_tbd")))
    _loan = _step * _lvr
    delta = _pay(_loan) or 0
    prh += "<p>%s</p><p>%s</p>" % (t("mortgage", lvr=_lvr_s, step=money(_step), loan=money(_loan), delta=money(delta), rate=_rate * 100, years=_years),
                                  esc(pr.get("bank_valuation_note")) or t("bank_val"))
    manual.append(("bank valuation", t("bank_val")))
    S.append(sec("s5", '<p class="ai-note">%s</p>' % esc(t("ai_note")) + scat + "<p>%s</p><p class=\"note\">%s %s</p>%s%s%s" % (t("comp_lead"), esc(cp.get("source_note", "")), esc(cp.get("filter_note", "")), cards_html, plvh, prh)))

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
    _miss = [r for r in figures_check(d) if not r[3]]
    for r in _miss: warnings.append(fig_warning(r))
    if _miss and edition == "internal":
        glh += "<h3>%s</h3><ul>%s</ul>" % (t("figs_missing"), "".join("<li><b>%s</b> (%s · %s): %s</li>" % (esc(r[4]), esc(r[0]), esc(r[1]), esc(r[2])) for r in _miss))
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
subject*: address*, lat, lon, map_url, streetview_url (hero Map / Street View links; default = Google Maps search / lat,lon street view), lot_dp, land_m2*, list_price*, built, dwelling, title_type torrens|strata|community, strata_m2 (unit: strata lot area incl. balcony/car/storage; shown instead of land), beds, baths, cars, floor_m2, status_line, status_class ok|warn|bad (hero panel), facts [[label, value], ...] (overview grid; rows that repeat the hero panel - address, beds/baths/cars, built, list price, last sold, Domain/AVM estimate - are skipped), land_value {latest, date, history {year: value}}
photos: images [{url, caption}] (hot-linked from the listing site's own URLs exactly as served, credited, never downloaded), credit_source, before_after [{before, after, caption}] (internal edition only), sources [{name, url, ok (true/absent = ✓, false = ✗), crosscheck (hover text)}] (shown as source-check chips in the hero), streetview_url, material_from_photos (shown as one overview facts row)
summary*: verdict_line*, max_risk*, range [lo, hi]*, range_note, avm_range [lo, mid, hi] (free Domain estimate, optional), offer {first (OPTIONAL: when missing the hero, tier table and mortgage block say it is set after talking to the agent), walk_away, confidence, confidence_note},
          cards: 5 x {label, status ok|warn|bad|cond|na, value, note, next}  (preferred over status_cards; if both absent, five placeholder cards with the default labels are shown —
                 house: flood / bushfire / landslip category / measured slope / development potential; unit: flood (basement/lobby) / bushfire / noise & arterial roads / strata health check / planning & supply)
status_cards: same shape as summary.cards (older files; still read)  (flood: bad = mainstream / High–Medium hit = veto; cond = Overland Flow / Low-PMF hit = conditional)
UNIT MODE: on when subject.title_type == "strata", subject.dwelling contains unit/apartment/flat/公寓/单元, or lot_dp contains an SP number.
  It relabels the hero area (strata lot) and land value (parent lot, entitlement needs a person), scores (land -> area & cars, slope -> level·aspect·view),
  completeness (floor_m2, cars, level, orientation|aspect, built, reno, levies, date & price; bookend needs >= 4/8), comps chart x = floor_m2,
  hides the P/LV block, and titles section 4 "Parent lot & building" (no site / profile / street-scatter figures there: stack_svg, building_svg, building_read and building_sales are used instead).
timeline: [{date, event, source, kind sale|rent|list|price_change|other (marker shape; guessed from the event text when absent), price (number; when absent the first $… amount in `event` is used)}]
dom: months_approx, basis, suburb_median_dom, suburb_dom_source, price_history_text, price_history_status verified|unverified, price_history [{date, price}] (>= 2 entries draw the list-price step chart against summary.range)
ruler: prices [..], list, window_label, n, median, min, max
hazards*: [{item, status ok|warn|bad|cond|na, tier covered|uncovered|paid, result, source, date, note, next*, slug}]  (status cond adds the two fixed flood next steps automatically)
land: facts [[label, value]], site_svg (file path or inline <svg>), profile_svg (house: always drawn), profile_flat {street, rear, fall} (adds a one-line note on flat sites; the chart stays), ring [[lon, lat], ...] (cadastral lot boundary drawn on the map), lv_note, street_sales [{addr, price, date, land, strata true (house mode: blank Land cell + note), floor_m2 (older unit files)}]
  unit mode ignores site_svg / profile_svg / street_sales charts and uses: stack_svg (same stack x floor), building_svg (same layout x sale date) - file path relative to data.json, or inline <svg> - building_read (one line under them),
  building_sales [{unit, beds, baths, cars, floor_m2, price, date, source}] (all sales in the building, unfiltered, shown newest first)
comps: source_note, filter_note, profile_url_pattern (e.g. https://www.domain.com.au/property-profile/{slug}; builds a link per comparable from its address + the subject's suburb/state/postcode), subject {land_m2}, p_lv_note, items (lettered A, B, C… in order) [{address, url (optional, wins over the pattern; matrix row, card title and map marker link to it), thumb (optional image URL, hot-linked exactly as served, credited, never downloaded - same rule as photos.images; shown as a small thumbnail on the card), price, date, dist_m, lon, lat, land_m2, lv, lv_m2, p_lv, landslip, street_side, elev, beds, baths, floor_m2, built, storeys, wall, reno,
       level, orientation (or aspect), view, cars, levies (unit fields),
       scores {land, slope, condition: +1|0|-1|null}, verdict (optional override; all three scores null -> "Unknown": grey, collapsed, never a bookend), bookend upper|lower|null, note}]
pricing: method_note, bookend_upper_text, bookend_lower_text, first_offer_text (tier-table basis of the first-offer row), upper / lower (legacy aliases of the two bookend texts only), widen_reason (shown as a 'Range note'),
         mortgage {rate (decimal: 0.0615 = 6.15%), years, step, lvr (decimal, default 0.8)}, bank_valuation_note
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
    ap.add_argument("--check", action="store_true", help="with --data: list the standard figures data.json cannot produce (house / unit aware), as WARNING lines; writes nothing; exit 0 unless the data file is unreadable")
    a = ap.parse_args()
    if a.schema:
        print(SCHEMA); return
    if not a.data or (not a.out and not a.check):
        ap.error("--data and --out are required (or use --schema / --check)")
    global LANG
    if a.check:
        try:
            with open(a.data, encoding="utf-8") as fh: d = json.load(fh)
            if not isinstance(d, dict): raise ValueError("top level is not an object")
        except (OSError, ValueError) as e:
            print("ERROR: cannot read %s: %s" % (a.data, e), file=sys.stderr); sys.exit(2)
        d["_path"] = os.path.abspath(a.data)
        if a.lang: d.setdefault("meta", {})["lang"] = a.lang
        LANG = (d.get("meta") or {}).get("lang", LANG)
        res = figures_check(d); miss = [r for r in res if not r[3]]
        print("check: %s mode, %d standard figures apply" % ("unit" if is_unit(d) else "house", len(res)))
        for r in miss: print("WARNING: " + fig_warning(r))
        print("check: %d/%d producible, %d missing (nothing written)" % (len(res) - len(miss), len(res), len(miss)))
        return
    with open(a.data, encoding="utf-8") as fh: d = json.load(fh)
    d["_path"] = os.path.abspath(a.data)
    if a.lang: d.setdefault("meta", {})["lang"] = a.lang
    title, banner, summary, sections, foot, warnings = build(d)
    with open(a.template, encoding="utf-8") as fh: tpl = fh.read()
    out = (tpl.replace("{{LANG}}", "zh-CN" if LANG == "zh" else "en").replace("{{TITLE}}", esc(title)).replace("{{BANNER}}", banner)
           .replace("{{SUMMARY}}", summary).replace("{{SECTIONS}}", sections).replace("{{FOOTER}}", foot)
           .replace("{{EXPAND_ALL}}", t("expand_all")).replace("{{COLLAPSE_ALL}}", t("collapse_all")).replace("{{TOOLBAR_HINT}}", t("toolbar_hint")))
    with open(a.out, "w", encoding="utf-8") as fh: fh.write(out)
    for w in warnings: print("WARNING:", w, file=sys.stderr)
    print("written", a.out, len(out), "bytes")

if __name__ == "__main__":
    main()
