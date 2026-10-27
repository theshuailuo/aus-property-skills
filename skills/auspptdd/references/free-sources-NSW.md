# NSW 免费数据源手册:事实、挂牌、市场、犯罪、公屋(方法版)

这里只写「去哪取、怎么取、口径是什么、取不到怎么写」。一套房的实测数字(用来对照方法是否跑通)在 `example-NSW.md`。付费站免费层能看到什么,见文末第 9 节。

---
## 1 物业事实主源:Aussie / Cotality 物业页(E4 裁决)
- URL:`https://www.aussie.com.au/property/nsw/<suburb-slug>-<postcode>/<address-slug>/`(slug 全小写、空格转连字符、街型写全称:`112a-salamander-way`,不是 `112a-salamander-wy`)。`curl` 带浏览器 UA 稳定 200;页面是 Cotality 数据。
- 能拿到:建年(`built in YYYY`)、房型卧卫车(FAQ 段 "includes N bedrooms, N bathrooms and parking for N cars")、建筑面积(`N sqm of floor space`)、土地面积、层数、**挂牌月份与现价**(Property history: "Listed for sale Feb 2026 For Sale @ $…")、上次成交、**出租记录**(Rental <月> $/周)、suburb 中位价与 12 月涨幅。
- 页内 JSON-LD 另有:`datePosted`(精确挂牌日,比「Listed Sep 2026」好)、`RealEstateAgent.name`(中介行)、`geo`、`image`(但 HTML 只含 1 张 og:image,其余 JS 加载)、`RealEstateListing.description` 全文(WA 中介在里面写 Strata / Council / Water / Level / Total Strata Lots);`aussie_slow_fetch.py` v0.4 全部输出。unit 的 `land` 字段是 strata lot 总面积,不是土地。
- 拿不到:外墙/屋顶建材、逐次调价史、AVM。
- 限速:每页之后 `sleep 75`,仍会间歇返回 202(空页)。`scripts/aussie_slow_fetch.py` 已带重试;18 笔可比约 45 分钟,**后台跑**。三次都 202 的,卡片写「未取到(限速)」并进「要人做」。**同楼批量取不可行**(第一页 200 后其余全部 202,16 分钟只得 1 页;连抓 8 页后几分钟内重试无效):同楼成交走 §2 的 Domain 楼栋页,脚本连续 2 页 202 即提前退出。
- 备选同源:OnTheHouse `https://www.onthehouse.com.au/property/nsw/<suburb>-<postcode>/<address-slug>`(页面内嵌 state JSON,地址页常只有搜索壳);OnTheHouse **成交列表** `onthehouse.com.au/sold/<state>/<suburb>-<pc>?page=N`(24 笔/页、12 个月窗口、含价格与房数,`curl` 无限速,`scripts/oth_sold_list.py`)是没有官方成交层的州(WA/VIC/QLD…)唯一免费带价源。

## 2 REA / Domain:只能用用户自己的浏览器
- realestate.com.au 对脚本有 Kasada 防爬:`curl` 固定 429;会话内 Browser 面板也可能按安全策略拒开。**让用户在自己的 Chrome 打开**(Claude in Chrome 插件可读页面文字),能打开就加:挂牌照片链接、挂牌文案(装修状况、建材线索)、suburb 页 median DOM、已售列表。
- Domain(`domain.com.au`)同理;它显示的 "listed for N days" 是**当前挂牌轮次**,常低估真实在市天数,报告注明口径。
- 打不开:不等、不重试超过一次,按 SKILL.md「照片多源回退」与「付费/人工数据固定口径」写。
- **Domain 物业档案页**(`https://www.domain.com.au/property-profile/<地址 slug>`,例 `112a-salamander-way-salamander-bay-nsw-2317`;会话浏览器可开,`curl` 403——NSW、WA 两次冷跑均如此)免费给:现挂牌价与「Listed on」日期、Domain 估值区间(低/中/高 + 置信)、租金估与收益率、历史成交(价、中介、**每次在市天数**)、区均售出天数、空置率、洪水/山火/heritage overlay 提示、学区、人口;unit 还给户型、室内面积、建年与 **Building Profile 入口**。挂牌页本身(`/<slug>-<listingId>`)给照片(图片 URL 原样热链,改尺寸路径会 400)、全文案(含 strata / water / council 支出与产权面积构成)、中介、开放时间;档案页不直接给挂牌链接时,从页内图片 URL 前缀 `<listingId>_1_1_…` 反推 id 再拼。
- **Domain 楼栋页(unit 同楼成交史正源)**:`https://www.domain.com.au/building-profile/<address-slug>?filtertype=sold&pagesize=10&pageno=N`。会话浏览器可开,但内容在卡片里,`get_page_text` 读不到:在页内用浏览器 JS 工具跑 `scripts/domain_building_profile.js`(`fetch` 各页 + DOMParser,解析规则 `a[href*="/property-profile/"]` 最近卡片文本匹配 `^(\$[\d.,]+[km]?|N/A)\s*(\d+[A-Z]?)/<门牌> … (\d{4})\s*([A-Z][a-z]{2})\s*(\d{1,2})`),一次拿全(North Sydney 25 页 206 笔含 N/A 未披露,20 秒),存 `building.json` 喂 `unit_stack_svg.py` 与 `nsw_comps_enrich.py --building-json`。
- **Allhomes**(`allhomes.com.au`)对 `curl` 可取,同楼 sold 列表含部分价格(North Sydney 37 笔),是脚本可读源里最好的;property.com.au 429、ratemyagent 403。

## 3 照片多源回退与交叉核对(E4)
顺序:REA → Domain → property.com.au → onthehouse / Aussie → 中介自己的网站(搜 `"<地址>" <中介名>`)。每一源都要**交叉核对至少三项一致**(地址、卧卫数、土地或建筑面积、挂牌价、中介名任三项)才算同一套房;只放链接与小图,不下载不转存。能看到照片时,AI 从照片判读外墙(砖 / 木板 weatherboard / fibro / 渲染 render)与屋顶(瓦 / 彩钢),报告写「从照片判读」(data.json 里不要带这个前缀,生成器会加);看不到照片时建材写「未知」并进「要问中介」。**无人值守时通常只得 1 张**(Aussie 页的 og:image,其余由 JS 加载):报告放这 1 张缩略图 + 挂牌链接,建材「未判」。

## 4 挂牌时长、调价史(#22;SKILL.md 报告写法 d)
| 层级 | 源 | 取法 | 得到 |
|---|---|---|---|
| 1 | Aussie 物业页 | JSON-LD `datePosted`(精确日)或 Property history 的 "Listed for sale <月 年>" | 首挂日 → 「约 N 个月」 |
| 2 | Domain 物业档案页(第 2 节,**只能浏览器开,curl 403**)或 REA / Domain suburb 页 | property-profile 的「Listed on」+ 历史成交的 days listed + 区均售出天数;suburb profile 的 median days on market | 本套上架日期、上次成交在市天数、区均在市天数(不是本套) |
| 3 | web.archive.org 对挂牌页的历史快照 | `https://archive.org/wayback/available?url=<REA 物业页 URL>`;有快照就逐个 `web/<timestamp>id_/` 取页面读当时价格 | 重建调价史(免费、慢;在售中的房通常没有快照) |
| 4 | oldlistings.com.au | `https://www.oldlistings.com.au/real-estate/NSW/<Suburb>/<postcode>/buy/1/<STREET>`(`curl` 可取) | 只收已下架的挂牌;同街邻居的历史 guide 价有;标的在售时查不到,下架后可复查 |
| 5 | 聚合站冻结价(realestateinvestar 等) | `curl` | 某一时点的价格快照,无日期戳,只作旁证 |
都拿不到 → 用 SKILL.md 的固定口径(问中介 / 买家代理 / 付费数据)并打问号「挂牌时长未验证」。

## 5 市场:空置率、在售库存、要价、租金(SQM Research 免费页)
口径是 **postcode**(不是 suburb),报告必须写明。页面数据嵌在源码 `var data = [...]` 里,`curl` 带浏览器 UA 即 200:
```
UA='Mozilla/5.0 (Windows NT 10.0; Win64) Chrome/124'
curl -sL -A "$UA" "https://sqmresearch.com.au/graph_vacancy.php?postcode=<PC>&t=1" -o vac.html            # 月度空置率 2005–:year,month,listings,properties,vr
curl -sL -A "$UA" "https://sqmresearch.com.au/property/total-property-listings?postcode=<PC>&t=1&hu=1" -o som.html   # 月度在售 2010–:houses,units
curl -sL -A "$UA" "https://sqmresearch.com.au/asking-property-prices.php?postcode=<PC>&t=1" -o ask.html  # 周度要价 2009–:houses_all,houses_3,units_all,units_2
curl -sL -A "$UA" "https://sqmresearch.com.au/weekly-rents.php?postcode=<PC>&t=1" -o rent.html           # 周度租金要价
# 提取:re.search(r'var\s+data\s*=\s*(\[.*?\]);', html, re.S) -> json.loads;scripts/sqm_fetch.py 已实现
```
要价与租金页各有 houses 与 units 两组序列:`sqm_fetch.py` v0.4 存 5 列 `[date, houses_all, houses_3, units_all, units_2]`,报告按产权类型取列(East Perth 邮编 6004 在售 188 套 unit vs 17 套 house,house 要价对公寓买家没有意义)。
另有 `/property/rental-yield`、`/property/total-rent-listings`、`/property/demographics` 同结构。要价周度样本小、波动大,只看趋势不看单点。
- 空置率:报最新月 + 12 个月均值 + 3 年前同月。
- 在售库存:报房/单元分开 + 同比 + 3 年前;在售龄分布(<30 / 30–60 / 60–90 / 90–180 / >180 天)可直接看「陈货占比」。
- **HtAG 公开页(2026-10-22 起)已把 Vacancy Rate / Days on Market 锁进付费层**(#14),不要再写它能拿到;未登录仍可见 typical price、各周期涨幅、IRSAD、租客占比。
- suburb 口径旁证(都 `curl` 可取,数值互相不一致,报告写明各自口径):realestateinvestar `https://www.realestateinvestar.com.au/Property/<suburb+name>`、OnTheHouse suburb 内嵌 state、OpenAgent `https://openagent.com.au/suburb-profiles/<suburb>-<pc>`、Smart Property Investment `https://www.smartpropertyinvestment.com.au/data/nsw/<pc>/<suburb>`。

## 6 长期增长 5/10/20/30 年
见 `state-NSW.md` 第 13 问(SIX 成交图层 2001 起逐年中位;30 年接 VG 年度 PSI 包或退到首府城市级 ABS/RBA 指数并注明)。HtAG 公开页的 1Y/3Y/5Y/10Y 涨幅可作旁证。

## 7 外墙建材
免费数据源没有建材字段(Aussie、REA 页都没有)。路径:① 照片判读(第 3 节);② Council DA 记录(1970 年后若有加建,描述里常写 brick/cladding);③ 进「要问中介」与「验房师 brief」。报告建材格写「未知(免费数据无)· 下一步:看房时目测;B&P 报告确认(验房师)」。

## 8 犯罪与公屋
见 `state-NSW.md` 第 11、12 问:BOCSAR `SuburbData.zip` 下载到独立目录用 `python -I` 抽、**必算全州每千人基线**;公屋 ABS Data API 报 SAL + SA2 两口径,SA1 要 DataPack。

## 9 付费站免费层一览(未登录实测,2026-10;写报告时按此决定哪些格子用固定口径)
| 站 | 未付费能看到 | 看不到 |
|---|---|---|
| SQM Research | postcode 级空置率、在售、要价、租金、收益率、人口(页面 JS 里) | 数据下载;suburb 口径 |
| HtAG | typical price、各周期涨幅、IRSAD、户型租金 | Vacancy、DOM、完整趋势线、周期位置、风险分(付费) |
| Cotality / RP Data(propertyvalue.com.au) | 被 Incapsula 拦,打不开 | — |
| Cotality 数据的免费出口 | Aussie 物业页(见第 1 节)、OnTheHouse、YIP(JS 图无数字) | AVM、调价史、建材 |
| PropTrack / REA | suburb 页(用户浏览器):median、12 月涨幅、在售数、DOM、5 年图(无数字) | 10 年以上;PropTrack 无公开 suburb 页 |
| Pricefinder / Stash / SuburbsFinder / Hotspotting / Suburbtrends | 首页或试用页,无数据 | 全部 |
| Microburbs | suburb 评分 9 项(Safety 等)、规划申请列表 | 价格预测、报告 |
| realestateinvestar / OpenAgent / Smart Property Investment | suburb 页:vacancy、stock、DOM、租金、收益率(各自口径) | 完整报告 |
| DSR Data | 免费配额常用尽 | — |
| oldlistings | 已下架挂牌史(街道页可 `curl`) | 在售中的标的 |
| Allhomes | 同楼 / 同街 sold 列表含部分价格(`curl` 可取) | 面积、楼层 |
| OnTheHouse | 成交列表(12 个月、含价)、单元页(面积、strata lot 面积、文案、成交史)、AVM 带(模型值) | 12 个月以前的成交 |
| property.com.au / ratemyagent | 脚本 429 / 403 | — |
