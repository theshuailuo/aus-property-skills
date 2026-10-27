# 数据源登记 · Data source registry

每个 skill 用到的外部数据源都登记在这里。新增来源先登记再用。
Every external data source a skill uses is registered here before use.

字段说明:**免费/付费**(免费 = 无需登录或订阅);**访问方式**(网页 / API / 下载包 / 只能用户自己的浏览器);**条款要点**(能不能自动取、能不能放进报告);**最后核验**(有人实际打开并取到数的日期)。没核过写「待核」,不猜。

| 来源 | 州 | 用途 | 免费/付费 | 访问方式 | 条款要点 | 最后核验 | 用到的 skill |
|---|---|---|---|---|---|---|---|
| ArcGIS World Geocoder(geocode.arcgis.com) | 全国 | 地址 → 坐标;单元地址返回楼栋点 | 免费 | API | 免登录;只用作定位 | 2026-10-28 | auspptdd |
| NSW Spatial Services SIX(maps.six.nsw.gov.au:Valuation L1/L5/L9、NSW_Cadastre L9) | NSW | 地价 5 年史、最近一笔成交、地块边界、Lot/DP 或 SP | 免费 | 图层服务(ArcGIS REST) | 政府公开图层;L5 不能点查,按 propid / 地址查;L1 每物业只留最近一笔、strata 稀疏 | 2026-10-28 | auspptdd |
| NSW 规划与环境图层(mapprod3.environment.nsw.gov.au:EPI、Hazard、Protection、BFPL、SEPP_Housing_2021、DA_Tracking) | NSW | 分区、限高、FSR、heritage、洪水(仅 10 个 LGA)、滑坡、山火、ANEF、TOD/LMR、DA | 免费 | 图层服务 | 政府公开图层;空返回只在图层覆盖该 LGA 时作「未检出」 | 2026-10-28 | auspptdd |
| NSW Spatial Services 主题图层(portal.spatial.nsw.gov.au:Transport、Elevation) | NSW | 路网等级、铁路(含隧道字段)、等高线 | 免费 | 图层服务 | 只允许 outFields=* + distance | 2026-10-28 | auspptdd |
| Council ArcGIS 服务(Northern Beaches、Port Stephens、North Sydney) | NSW | council 洪水 / 山火 / 滑坡 / heritage 层;North Sydney 只有分区层,洪水为 PDF | 免费 | 图层服务 / PDF | 各 council 公开;配置见 skill `templates/council-*.json` | 2026-10-28 | auspptdd |
| NSW legislation(legislation.nsw.gov.au)经 web.archive.org 快照 | NSW | LEP / Housing SEPP 条文 | 免费 | 网页(官网 403,用 `web.archive.org/web/2id_/` 快照) | 政府法规文本;报告注明快照日期 | 2026-10-22 | auspptdd |
| NSW Valuer General PSI 年度包 | NSW | 1990–2000 成交(30 年增长) | 免费 | 下载包(浏览器下载) | 政府公开数据 | 2026-10-22 | auspptdd |
| BOCSAR SuburbData.zip | NSW | 郊区犯罪计数 + 全州每千人基线 | 免费 | 下载包 | 政府公开数据;下载到独立目录用 `python -I` 读 | 2026-10-28 | auspptdd |
| ABS Data API(C21_G37、ERP_Q) | 全国 | 公屋、租住比、人口 | 免费 | API | CC BY 4.0 | 2026-10-28 | auspptdd |
| SQM Research 免费页 | 全国(postcode 口径) | 空置率、在售库存、要价、租金(house 与 unit 两组) | 免费 | 网页(数据嵌在源码) | 引用数字并注明来源与 postcode 口径;不转存整表 | 2026-10-28 | auspptdd |
| Aussie / Cotality 物业页(aussie.com.au/property) | 全国 | 建年、卧卫车、面积、挂牌日、价格、租赁记录、文案(JSON-LD) | 免费 | 网页(`curl` 200,约 75 s/页,202 限速;同楼批量不可行) | 只取事实与一张 og:image 缩略图链接 | 2026-10-28 | auspptdd |
| Domain 物业档案页与楼栋页(domain.com.au/property-profile、/building-profile) | 全国 | 估值区间、租金估、在市天数、同楼全部成交 | 免费浏览 | **只能浏览器**(脚本 403);楼栋页用页内 JS 取 | 照片只放链接 + 小图;数据只用于本报告 | 2026-10-28 | auspptdd |
| realestate.com.au | 全国 | 挂牌照片、文案、suburb 页 | 免费浏览 | **只能用户自己的浏览器**;脚本 429 | 照片只放链接 + 小图,见 `../images-policy.md` | 2026-10-22 | auspptdd |
| OnTheHouse 成交列表与单元页(onthehouse.com.au/sold) | 全国(无官方成交层的州的主源) | 12 个月成交、价格、房数、面积、strata lot 面积 | 免费 | 网页(`curl` 可取,无限速;脚本间隔 2 s) | 只取成交事实;AVM 带标「模型值」 | 2026-10-27 | auspptdd |
| Allhomes(allhomes.com.au) | 全国 | 同楼 / 同街 sold 列表 | 免费 | 网页(`curl` 可取) | 只取成交事实 | 2026-10-28 | auspptdd |
| OSRM 公共路由(routing.openstreetmap.de) | 全国 | 步行距离(LMR 800 m、车站) | 免费 | API | ODbL;只取距离 | 2026-10-22 | auspptdd |
| WA Landgate SLIP Public Services(Places_and_Addresses、Property_and_Planning、Water、Transport、Terrain、Education 等) | WA | 地址多边形、Plan Extent / SP、分区、R-Codes、heritage、DWER 洪水四层 + 洪水位点、山火、ASS、污染场地、噪音走廊、等高线、校点 | 免费 | 图层服务 | 政府公开图层,免登录;DA 登记需 SLIP 登录(不用) | 2026-10-27 | auspptdd |
| Main Roads WA Traffic Digest | WA | 车流量 AADT | 免费 | 下载 | CC BY 4.0 | 2026-10-03 | auspptdd |
| Landgate strata 页(strata-and-community-titles) | WA | strata plan 副本价格、买家披露要求 | 免费(副本付费 $33.90) | 网页 | 只引用价格与要求 | 2026-10-27 | auspptdd |
| VIC Planning 地图(planning.vic.gov.au / mapshare) | VIC | 规划与覆盖层 | 免费 | 网页 + 图层服务 | 待核 | 待核(手册草拟,未冷跑) | auspptdd |
| QLD 空间数据(spatial-gis.information.qld.gov.au) | QLD | 规划、灾害 | 免费 | 图层服务 | 待核 | 待核(手册草拟,未冷跑) | auspptdd |
| SA SAPPA(sappa.plan.sa.gov.au) | SA | 规划与地块 | 免费 | 网页 + 接口 | 待核 | 待核(手册草拟,未冷跑) | auspptdd |
| TAS theLIST | TAS | 规划、地块、灾害 | 免费 | 图层服务 | 待核 | 待核(手册草拟,未冷跑) | auspptdd |
| NT NTLIS | NT | 地块、规划 | 免费 | 网页 + 图层服务 | 待核 | 待核(手册草拟,未冷跑) | auspptdd |
| ACT Revenue / ACTmapi | ACT | 税费、地价、规划 | 免费 | 网页 | 待核 | 待核(手册草拟,未冷跑) | auspptdd |

> auspptdd 的行按 2026-10-22/23/27/28 四次冷跑实际取到数的日期填写;标「待核」的州只有手册,还没跑过。
> auspptdd rows carry the dates on which a cold run actually retrieved data; states marked 待核 have a manual but no cold run yet.

## 付费数据(本仓库不用,只记录「为什么重要、谁能补」)

| 来源 | 为什么重要 | 谁能补 |
|---|---|---|
| Cotality(原 CoreLogic)/ RP Data | 逐次调价史、AVM、完整可比 | 有订阅的买家代理、中介、贷款经纪 |
| HtAG 付费层 | 空置率与在售天数(2026-10 起已锁进付费层) | HtAG 订阅用户 |
