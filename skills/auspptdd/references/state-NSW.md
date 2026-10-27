# NSW 州适配:九问的查询写法与判读(公开版正本)

本文件是 NSW 的完整查询手册:每一问给服务地址、图层号、where 写法、字段与判读。全部是免费公开接口,`curl` / Python `urllib` 即可,不需要登录。坐标一律 `inSR=4326`(经度在前)。图层号与字段名以当场实测为准,文末「变更记录」记录每次改动。实例数据(一套已跑过的房)单独放在 `example-NSW.md`,正文只讲方法。

通用点查模板(下文「点查 L{n}」都指它):
```
<服务>/<n>/query?f=json&geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false
```
查「最近的多边形离标的多远」:加 `&distance=500&units=esriSRUnit_Meter&returnGeometry=true&outSR=4326`,在客户端算点到多边形边的最小距离(`scripts/nsw_layers.py` 已实现)。
图层返回 0 条只有在「图层覆盖该 LGA 且阳性对照能命中」时才写「未检出 · 目前看风险较低」;不覆盖该 LGA 的图层一律写「未覆盖」。

服务地址缩写(全文沿用):
- `SIXV` = `https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer`
- `CAD` = `https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer`
- `EPI` = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/EPI_Primary_Planning_Layers/MapServer`
- `HAZ` = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Hazard/MapServer`
- `PRO` = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Protection/MapServer`
- `BFPL` = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer`
- `SEPPH` = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/SEPP_Housing_2021/MapServer`
- `DA` = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/DA_Tracking/MapServer`
- `ELEV` = `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Elevation_and_Depth_Theme/MapServer`
- `TRANS` = `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Transport_Theme/MapServer`

---

## 0 地址 → 坐标
`https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?f=json&singleLine=<地址>, NSW&maxLocations=1&outSR=4326`
读 `candidates[0].location.x/y` 与 `score`(<90 分要人工确认门牌)。街名常被口头缩略("Upper Avenue" 实为 "Upper Avenue Road"),以 geocoder 返回的 `address` 为准。

## 1 地块:lot / plan、面积、边界、是否 strata
| 要什么 | 查哪里 | 写法 | 判读 |
|---|---|---|---|
| Lot / DP(或 SP) | `CAD` L9(Lot) | 点查 L9,`outFields=*` | 读 `lotidstring`(形如 `111//DP204344`)或 `lotnumber` + `planlabel`。plan 前缀 **DP = Torrens(含 community title)**,**SP = strata**;SP 一律按 unit 流程 |
| 地块边界(画图、算坡) | `SIXV` L9(Property boundary) | 点查 L9,`returnGeometry=true&outSR=4326` | `features[0].geometry.rings[0]` 为经纬度环;`attributes.propid` 是后面查地价的钥匙 |
| 面积、地价、分区文字 | `SIXV` L5(Urban Property Valuations) | **不能点查**(L5 对坐标点查返回空,见变更记录 #3)。按属性查:`where=propid=<L9 的 propid>`,或 `where=address LIKE '<门牌 街名 街型>, <郊区>%'`(地址全大写、街型缩写 CRES/RD/AVE/PDE/PL/ST、后接逗号与郊区;禁用前置通配 `LIKE '%…'`,会全表扫描超时)。**`outFields` 一律写 `*`**:点名一个 L5 没有的字段(如 `strata`)整条查询 400「Failed to execute query」 | `prop_area`(字符串 "556.4 square metres",自己取数字)、`zone_desc`、`val1_lv…val5_lv`(字符串 " $1,150,000",近 5 年地价,val1 为最新)、`val1_bd…val5_bd`(基准日) |
| 是否已 strata 化 | `SIXV` L1(Urban Property Sales) | `where=propid=<propid>` 或 `suburb='<郊区>' AND street LIKE '<街名>%'` | `strata` 字段非 0 = strata;L1 还给 `price`、`sale_date`、`area`(最近一笔成交) |
| L4(Property Valuations) | — | **弃用**:任何参数都 400「Invalid or missing input parameters」(#4) | 只用 L5 |

strata 单元在 L5 没有逐户记录;母地块按门牌(不带单元号)查,得到的是整栋地价。**SP 地块的四条实测(2026-10-28,North Sydney 18 层公寓):**
1. `CAD` L9 点查到的多边形可能只是一片 stratum 碎片(`lotidstring="//SP96878"`、`lotnumber=null`、`hasstratum=2`,实算 224 m² 而 `planlotarea` 514 m²),**不能当基地面积**;基地面积取 `SIXV` L5 的 `prop_area`。
2. L5 按母地址查可能返回**多行、多个 propid**(一个基地两个 strata scheme:7,383 m² / LV $54.7M 与 4,441 m² / $11.5M,且有重复行):按 propid 去重后全部写进报告,「母地块地价(每 scheme)」+「本单元份额 entitlement 需人」。`prop_area` 对 strata 也不是楼栋占地。
3. L1 的 unit 行 `house_no` 形如 `1503/150`,`strata` 字段是 scheme id(非 0 即 strata);但 L1 每物业只留最近一笔、strata 覆盖极稀(见 §13),同楼成交史不能靠它,走 `free-sources-NSW.md` §2 的 Domain 楼栋页。
4. 规划条文的 LEP 编号就是 `EPI` L2 分区返回的 `PCO_REF_KEY`(如 `2013-411` → `epi-2013-0411`),不必猜。

## 2 规划分区与 overlay;LEP 条文
### 2.1 图层(`EPI`)
| 图层 | 内容 | 关键字段 |
|---|---|---|
| L0 | Heritage(含 conservation area) | `LAY_CLASS`、`SYM_CODE`、`H_NAME` |
| L1 | FSR 容积率 | `FSR`、`SYM_CODE`(无 FSR 地图的 LGA 返回空,例如前 Warringah 区用 DCP 的 Landscaped Open Space 控制) |
| L2 | Land Zoning | `SYM_CODE`(R2/R3…)、`LAY_CLASS`、`EPI_NAME`(LEP 名)、`LGA_NAME` |
| L3 | Land Reservation Acquisition | 命中 = 可能被征收,红旗 |
| L4 | Lot Size 最小地块 | `LOT_SIZE`、`UNITS`、`SYM_CODE`;可能返回多条(主控 + 例外区),`LEGIS_REF_CLAUSE` 指向条款号,**必须去读条文** |
| L5 | Height of Buildings | `MAX_B_H`、`UNITS` |
| L6 | Land Application(LEP 适用范围) | `EPI_NAME` |
所有图层都带 `COMMENCED_DATE`、`CURRENCY_DATE`、`AMENDMENT`,报告写图层名 + 查询日期。

### 2.2 LEP / SEPP 条文怎么拿(#8、#9)
- LEP 编号在 L2 的 `EPI_NAME`(例:Warringah LEP 2011 = `epi-2011-0649`;不知编号时在 `https://legislation.nsw.gov.au/browse/inforce` 搜 LEP 名)。
- 正式地址 `https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-<编号>`:`curl` 固定 403;浏览器会停在 Cloudflare「正在进行安全验证」人机页(不许代点)。
- **可用路径:web.archive.org 原样快照**(`id_` 后缀返回原始正文,不加存档站的包装):
  ```
  curl -sL -A "Mozilla/5.0" "https://web.archive.org/web/2id_/https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2011-0649" -o lep.bin
  python -c "import gzip;b=open('lep.bin','rb').read();open('lep.html','wb').write(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b)"
  ```
  返回体可能是 gzip 二进制(`curl -L` 不自动解压),先判断前两个字节 `1f 8b` 再解压;快照日期在响应头 `x-archive-orig-date` / `memento-datetime`。**报告必须注明「条文为 web.archive.org 存档快照(日期),出价前由律师按现行版复核」**。没有快照时(`https://archive.org/wayback/available?url=<URL>` 返回空),改列「要人做:浏览器打开官网过人机验证后读条文」。
- 必读:① 该 zone 的 Land Use Table(permitted with consent:dual occupancy / secondary dwelling / multi dwelling / RFB)——**在拉平的文本里先定位 "Land Use Table" 再找分区名**(标题会拆成 "Zone C4" / "Environmental Living" 两行,直接搜整句只会命中各条款里的引用);**非住宅分区(C2/C3/C4/R5/RU)的 granny flat 与双拼只看这张表和 cl 4.1 系列 + 本地条款(例如 Port Stephens cl 7.15),Housing SEPP 的 secondary dwelling(s 49–50 只列 R1–R5)与 LMR(s 164 排除 bushfire prone 与 flood planning 地)都不适用**;② cl 4.1 最小地块与 4.1A/4.1B 类例外(分割、双拼门槛;battle-axe 柄是否计面积);③ cl 4.3 限高与 4.3A 类附加;④ 本地灾害条款(例如滑坡 cl 6.x 要求岩土评估);⑤ 附属住宅面积上限条款。
- Housing SEPP 2021(`epi-2021-0714`)同法取快照,读 Ch 3 Pt 1 s 52–54(secondary dwellings:面积上限、最小地块、complying 路径)与 Ch 6(低中密度 LMR:s 163 定义、s 164 排除地、s 166–169 双拼与 LMR 非裁量标准)。

## 3 洪水(分档:主流 / High–Medium 命中 = 否决;Overland Flow / Low(PMF)命中 = 条件项,固定带「规划洪水位 vs 地板高度」与「保险报价」两个下一步)
- 州图层 `HAZ` L1 Flood Planning **只覆盖 10 个 LGA**(2026-10-03 实测 distinct `LGA_NAME`:Bathurst Regional、Clarence Valley、Forbes、Hornsby、Mid-Western Regional、Tamworth Regional、Wentworth、Wingecarribee、Wollongong、Yass Valley)。其余 LGA 返回 0 条只说明州图层没覆盖到,写「州图层未覆盖」,洪水判定交给 council 图层。
- 其余 LGA 走 council 自己的 ArcGIS 服务(下表);没接通的 council 写「免费数据不覆盖 · 下一步:council 洪水图 / 合同附的 Section 10.7 证书(律师)」,**这一格不许凭图层空返回写 ✓**。

### 已接通的 council 洪水接口
| Council | 服务 | 图层 | 实测 |
|---|---|---|---|
| Port Stephens | `https://services-ap1.arcgis.com/YixhBZMQhOb0beqS/arcgis/rest/services`(ArcGIS Online,每数据集一个 FeatureServer) | Flood_Planning_Area_/FeatureServer/2(`CategoryDescription`:Flood Planning Area / Flood Planning Area Overland Flow,2023-11);Flood_Prone_Land/FeatureServer/170(近乎全覆盖,只作旁注);Bushfire_Prone_Land/FeatureServer/161(2021);ANEF_2025/FeatureServer/175;Consolidated_CKPoM_Koala_Habitat_Map/FeatureServer/90;Drainage___Control_Areas/FeatureServer/3;Hydrologic_Soil_Groups/FeatureServer/129 等 13 层,见 `templates/council-port-stephens.json` | 2026-10-23 ✅ 阳性:Salamander Bay 岸边 Flood Planning Area;阴性:Nelson Bay 高地空;ANEF 对照 Williamtown 40+ |
| Northern Beaches | `https://maps.northernbeaches.nsw.gov.au/arcgis/rest/services/NBC_PWM_LEPs/MapServer` | 158 Flood Hazard;159 High / 160 Medium / 161 Low Flood Risk Planning Precinct(Low = PMF 范围,字段 `Risk`);93 Warringah Landslip Risk(`Zone` A/B/C);153 Bush Fire Prone Land 2020(`Category_txt`);84 HOB、86 Lot Size、87 FSR、91 Heritage、92 ASS、52 Riparian、54 BioCert、57 Landscaped Open Space | 2026-10-22 ✅ 点查 + `distance=500` 最近距离查询均可;阳性对照:Warringah Mall(Old Pittwater Rd)命中 Medium,Manly Lagoon(Riverview Pde)命中 High |
| North Sydney | `https://services-ap1.arcgis.com/33nKDOPkQG7pavgq/arcgis/rest/services`(ArcGIS Online,只有分区与边界层) | `Land_Zoning_Public/FeatureServer/40`(`zoning`)。**无洪水 / 山火 / heritage / 限高 / FSR 层**:council 互动地图是 SIS WebMap(非 ArcGIS,无 REST);洪水只有 2022-11《Floodplain Risk Management Study and Plan》PDF;heritage / FSR / 限高走州 `EPI` L0 / L1 / L5(配置里的 `state_fallback`);州 `HAZ` L1 对 North Sydney 0 条 | 2026-10-28 ⚠️ 洪水卡只能写「未覆盖 · PDF 链接」+ 10.7 证书;配置 `templates/council-north-sydney.json`(含 `state_fallback` 与 `pdf_maps` 两块,`nsw_layers.py` 自 v0.4 起读) |

找新 council 接口(两条路):
1. council 自建 ArcGIS Server:打开该 council 洪水页 → 找「online mapping / flood hazard map」→ `curl` 该页源码 grep `rest/services` → 列服务目录找名字带 flood / hazard / LEP 的图层(Northern Beaches 这种,一个 MapServer + 整数图层号)。
2. **ArcGIS Online / Experience Builder**(Port Stephens 这种,页面只嵌 `experience.arcgis.com/experience/<id>`,源码里没有 `rest/services`):`https://www.arcgis.com/sharing/rest/content/items/<id>/data?f=json` 读出所有 `itemId`;对每个 itemId 再读 `.../items/<itemId>?f=json`(`type` 为 Web Map 的读 `/data` 看 `operationalLayers[].url`;`type` 为 Feature Service 的直接取 `url`);得到 `services-ap1.arcgis.com/<org>/arcgis/rest/services/<Name>/FeatureServer/<n>`。每个数据集一个 FeatureServer,配置里的 `id` 写成字符串 `"<Name>/FeatureServer/<n>"`(`nsw_layers.py` 自 v0.3 起接受字符串 id)。样板:`templates/council-port-stephens.json`。
阳性 / 阴性对照的通用取点法:阳性点取最近水体(河、湖、海湾)岸线 50 m 内一点,阴性点取最近的山顶或高地(用 opentopodata 或等高线挑);两点都按预期返回才用这层。**近乎全覆盖的层(例如 Port Stephens「Flood Prone Land 2023」一张 192 km² 多边形,三个对照点全命中)只作旁注,不作判定。** 跑通一个就加进上表并记变更。`scripts/nsw_layers.py --council-config <json>` 可直接接入新 council(格式见脚本 `--help`)。

### council 只有 PDF 洪水图时怎么读
1. 搜 `<council> <catchment> flood study`,下载「100 Year Flood」与「Flood Risk Precincts」两张图(PDF)。council 官网对 `curl` 常 403,改 `https://web.archive.org/web/2id_/<原 PDF URL>`。
2. PyMuPDF 渲染总览 → 按街名裁局部 → 用 OSM 路口坐标和比例尺估标的位置。
3. 结论必带三条保留:定位误差多少米;地块在不在模型边界内(边界外 = 未建模,不是干);研究年份。最终以 Section 10.7 证书为准。

## 4 山火
- `BFPL` L0(RFS Bush Fire Prone Land):点查;`Category`(1/2/3)或 Vegetation Buffer;再加 `distance=1500` 取最近斑块距离与类别。council 常有自己的 BFPL 版本(Northern Beaches L153),两者都查、都写。
- 四要素判读,不只看命中:① 房屋是否被林地包围;② 最近植被斑块多大(`Shape_Area`);③ 距主林地多远;④ 植被类别。命中(含 buffer)= dual occ / LMR 新政排除项,红旗「新政资格需 bushfire planner 确证」。

## 5 滑坡、酸性硫酸盐土、其他敏感地、污染与沉降
| 项 | 图层 | 字段 / 判读 |
|---|---|---|
| 滑坡 | `HAZ` L2 Landslide Risk;council 版(NBC L93) | `LAY_CLASS` 如 "Area B - Flanking Slopes 5 to 25";A <5°、B 5–25°、C >25°。B/C = DA 需岩土报告(对应 LEP 滑坡条款);加 `distance=100` 看 C 区边界离多近 |
| 酸性硫酸盐土 | `PRO` L1 | `LAY_CLASS` Class 1–5(1、2 最严) |
| 机场噪音 | `PRO` L2 Airport Noise | `ANEF` ≥ 20 红旗 |
| 河岸 / 水道 | `PRO` L7 | 命中 = 建筑退界受限 |
| 景观保护 | `PRO` L9 Scenic Protection | 命中 = 高度/外观受限 |
| 生物多样性 | `PRO` L10 Terrestrial Biodiversity | 命中 = 清地受限 |
| 环境敏感地 | `PRO` L12 | 命中 = 新政排除项之一 |
| 污染场地 | 免费图层无 | 要人做:NSW EPA Contaminated Land public record(`https://www.epa.nsw.gov.au/your-environment/contaminated-land/contaminated-land-record`)按郊区搜;Section 10.7 证书第 2 部分 |
| 采矿沉降 | 免费图层无 | 要人做:Subsidence Advisory NSW 地图(`https://www.subsidenceadvisory.nsw.gov.au`);悉尼都会区多数不在 |
| 高压线、变电站、铁路、坟场、污水厂 | OSM Overpass(镜像不稳,见第 8 问) | 高压线 ≥500 m、铁路 ≥200–500 m、坟场/污水厂 ≥1 km;查不到时写「要人做:Street View / 卫星图看 X」 |

## 6 官方地价(Valuer General,免费)
`SIXV` L5 按 propid / address 查(写法见第 1 问),`val1_lv…val5_lv` 为近 5 年地价,`val1_bd` 为最新基准日(每年 7 月 1 日)。地价 ÷ `prop_area` = $/m²;同街邻居各查一遍可看出 VG 对低处/坡地/后排地块打了多少折。

## 7 DA / 规划申请(#7)
`DA` L0(NSW Planning Portal 全州 DA 点图层)。
- 标的本身:`where=UPPER(SITE_ADDRESS) LIKE '%<街名 街型>%' AND UPPER(SUBURBNAME)='<郊区>'`(**两段都用 UPPER(),郊区用等号**;把街名和郊区写进同一个 LIKE 会 400)。门牌再在客户端过滤。
- 邻里 300 m:点查 + `distance=300&units=esriSRUnit_Meter&outFields=*`,看同街加建、泳池、拆建的类型、状态、造价(常用字段:`SITE_ADDRESS`、`SUBURBNAME`、`DEVELOPMENT_DESCRIPTION`、`STATUS`、`LODGEMENT_DATE`、`COST_OF_DEVELOPMENT`;以 `outFields=*` 实测为准)。
- 供应端:`distance=3000` 筛 subdivision / apartment 类大型开发。
- Portal 只有 2017 年前后起的电子申请;更早的加建要靠 council 档案或 Section 10.7。没有 DA 记录时写「2017 年后无电子申请;更早的加建去 council 档案 / 10.7 查」。

## 8 道路等级、车流、铁路、噪音(#5、#6、#18)
- **道路优先用官方路网**:`TRANS` L5 RoadSegment。写法只能是点查 + `distance=<米>&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&outSR=4326`;**加 `where=roadnamebase IN (…)` 或自定义 `outFields` 都会 400**,所以取回来在客户端按 `roadnamebase` / `roadnametype` 过滤。字段:`roadnamebase`、`roadnametype`、`functionhierarchy`(1 = 高速/干线 … 6 = 本地街 … 9 = 小径;数字越小车越多)。标的 120 m 内取街段判「街在地块哪一侧」;1,500 m 内取 `functionhierarchy ≤ 4` 的路段算到干道距离。
- 铁路:`TRANS` L7 Railway,`distance=800`。**命中要分地面/地下**:字段 `railontype`(North Sydney 命中 186 m 的是 Sydney Metro Victoria Cross 隧道,`railontype=3`),隧道对地面噪音无意义,报告写「地铁隧道,无地面噪音;车站步行距离 X m」;`nsw_layers.py` v0.4 输出该字段并加 `underground_likely` 标记,CBD / North Sydney / Chatswood 一带命中多为隧道。
- 车流量 AADT:没有免费接口。**写进「要人做」**:TfNSW Traffic Volume Viewer(`https://www.transport.nsw.gov.au/operations/roads-and-waterways/corporate-publications/statistics/traffic-volumes`)按路名查最近计数站,买家代理或你自己 5 分钟。
- OSM Overpass 只作备选(2026-10-22 三个公共镜像同日全部失败:overpass-api.de 406、private.coffee 超时、mail.ru 证书错)。用时 POST `data=[out:json][timeout:25];way[highway](around:120,{lat},{lon});out tags geom;`。
- 步行距离(LMR 800 m、到车站/学校):`https://routing.openstreetmap.de/routed-foot/route/v1/foot/{lon},{lat};{lon2},{lat2}?overview=false` 读 `routes[0].distance`。

## 9 州政策与资格排除(SEPP Housing 2021)
`SEPPH`:L2 STRA、L3 TOD Sites、L4 Accelerated TOD、L5 Deferred TOD、L6 Town Centres(LMR 指定中心)。点查 + `distance=1200&returnGeometry=true` 取最近中心多边形,客户端算直线距离。
- 判定口径:法定 800 m **步行距离**。直线 >800 m 出局;直线 650–800 m 临界 → 用第 8 问的步行路由算实际步行距离,结果在 800 m ±15% 仍标「需规划师确证」;直线 <650 m 大概率适用。
- LMR 圈内非裁量标准(2025 版):R3 0–400 m 内 RFB 6 层 / 2.2:1;400–800 m 4 层 / 1.5:1;双拼 R2 全州 450 m² / 0.65:1 / 9.5 m。**排除项**:bushfire prone、flood、heritage item、环境敏感地等,以 s 164 原文为准。
- **LGA 本地版本优先于通则**:部分 council 与州谈了本地门槛(已知:前 Warringah 区 R2 双拼 ≥800 m²,Warringah LEP cl 4.1B,2025-10-31 起)。遇到新 LGA 先搜 `<council> dual occupancy low mid-rise` 确认,标注信源等级。门槛线 ±5% 的地块是期权分水岭。

## 10 地形:等高线、落差、街面侧(状态卡「实测坡度」)
- 等高线:`ELEV` L2(2 m 等高线),用地块环做多边形查询并外扩 45 m:
  `geometry={"rings":[<L9 ring>],"spatialReference":{"wkid":4326}}&geometryType=esriGeometryPolygon&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=elevation&returnGeometry=true&outSR=4326&distance=45&units=esriSRUnit_Meter`
  字段 `elevation`(米)。
- 街面侧:第 8 问取的街段与地块各边中点求最近距离,最近的那条边 = 临街边。
- 剖面:从临街边中点穿过地块形心到对边,两端各外延 14 m,与等高线逐段求交,得「离临街边界距离 → 高程」;街面高程取外延段。落差 = 临街边高程 − 后边界高程,坡度 = 落差 ÷ 进深。房屋低于街面(街面高、后院低)是实质减分项(排水、进门下行、挡土)。
- 旁证:`https://api.opentopodata.org/v1/srtm30m?locations={lat},{lon}|…`(30 m 格网,只作量级对照)。
- `scripts/nsw_lot_terrain.py` 一条命令做完上述并输出 ring.json / contours.json / roads.json / profile.json;`scripts/site_profile_svg.py` 画图。

## 11 犯罪(#16)
- 唯一免费权威源:BOCSAR 开放数据 `SuburbData.zip`(约 12.7 MB,解压后 CSV 约 440 MB;逐郊区 × 犯罪类别 × 月,1995 年起)。下载页 `https://bocsar.nsw.gov.au/statistics-dashboards/open-datasets/criminal-offences-data.html`,链接在页面源码里 grep `SuburbData`。
- 下载到**独立空目录**,用 `python -I scripts/bocsar_suburb_rate.py --zip <目录>/SuburbData.zip --suburb "<郊区>" --pop <郊区人口> --state-pop <全州人口>` 流式读取(不要整文件进内存)。
- **必须给基线**:同一份文件把所有郊区同期加总 = 全州总数,÷ 全州人口得「每千人」基线;再给标的郊区每千人。没有基线的「N 起/千人」买家读不懂。人口:郊区用 ABS QuickStats(SAL)或 HtAG 公开页;全州用 ABS 最新估计(写明取数日期)。
- 第三方镜像(gdp.com.au、yourpropertyguide)口径不一,只作旁证;Microburbs 免费页的 Safety 分可并列展示。

## 12 公屋(#17)
- ABS Data API(零下载,CSV/JSON):
  ```
  SAL 码:点查 https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/SAL/MapServer/0(字段 sal_code_2021 / sal_name_2021);SA2 码:同站 ASGS2021/SA2/MapServer/0(sa2_code_2021)
  curl -s "https://data.api.abs.gov.au/rest/data/ABS,C21_G37_SAL/..<SAL码>..?format=csvfilewithlabels"
  curl -s "https://data.api.abs.gov.au/rest/data/ABS,C21_G37_SA2/..<SA2码>..?format=csvfilewithlabels"
  ```
  维度顺序 `TENLLD.STRD.REGION.REGION_TYPE.STATE`;取 `TENLLD` = "Rented: State or territory housing authority" + "Rented: Community housing provider",`STRD` = Total,÷ 总住宅数。
- **报两口径**:SAL(郊区)与 SA2(社区),数字可能差一个量级(公屋集中在相邻郊区时);SA1(街区)ABS API 没有,要下载 Census DataPack(zip)——写「要人做」或下一次再补。
- `scripts/abs_g37.py --lon --lat` 一条命令出两口径。

## 13 长期增长 5/10/20/30 年(#15)
- 2001 年起:`SIXV` L1 Urban Property Sales 逐年查 `where=suburb='<郊区>' AND strata=0 AND sale_date LIKE '%2015'`(`sale_date` 是 "9 January 2012" 这种字符串;不要用 resultOffset/orderBy,会 400;每次 4–16 秒,逐年循环 26 次 2–7 分钟,后台跑)。按年取中位,用 3 年窗口平滑算 5/10/20 年年化。`scripts/nsw_sales_history.py` 已实现。注意:这是成交中位价,不是重复销售指数,有房型/地块混合效应;图层每物业只留最近一笔,早年样本有幸存者偏差。
- **30 年(1990–2000)**:SIX 图层没有。路径一:Valuer General 历年 PSI 年度包 `https://www.valuergeneral.nsw.gov.au/__psi/yearly/<YYYY>.zip`(1990–2000 每年一包,免费,`curl` HEAD 被 WAF 403,要浏览器下载到独立目录),`python -I scripts/psi_archive_median.py --zip <包> --suburb "<郊区>"` 算区级中位。路径二(接不上时):首府城市级指数——ABS 6416.0 Residential Property Price Indexes(2003 起)、更早的 ABS 6416.0 House Price Indexes: Eight Capital Cities(1986 起)或 RBA 统计表,**报告注明「市级指数,非本区」**。原因要写清:ABS 没有郊区级房价指数,只到首府城市级;区级 30 年只能靠 VG 逐笔成交自己算。

## Unit 在 NSW 的补充(SKILL.md「Unit path」的 NSW 查法)
- 洪水、山火、滑坡、heritage、ANEF 这几层 unit 同样查;洪水对高层的看点是地库 / 大堂 / strata 保险,固定两条下一步改成「地库与地面层高程 vs 规划洪水位」「strata 保单 + 两家报价」。
- **跳过 §10 地形**:`nsw_lot_terrain.py` / `site_profile_svg.py` 对 SP 自动停(v0.4);不停的旧版会对 stratum 碎片算出 33% 坡度、后巷临街这种误导值。
- Land content:母地块在 L5 查地价(按母地块门牌,不带单元号;多 propid 全列)× 该单元的 unit entitlement(strata plan 或合同附件;免费数据无,进「要人做」)。
- **同楼成交史正源 = Domain 楼栋页**(`free-sources-NSW.md` §2):会话浏览器开 `domain.com.au/building-profile/<slug>?filtertype=sold&pagesize=10&pageno=N`,用 `scripts/domain_building_profile.js` 一次取全(25 页 206 笔 20 秒);`get_page_text` 读不到卡片内容。**VG L1 对 strata 不可用**(North Sydney `strata<>0` 逐年:2001–2019 每年 0–5 笔,2024 年 23、2025 年 43、2026 年 65;`nsw_sales_history.py --strata` 会打印同样的警告)。unit 长期增长写「楼内同户型自身成交史」+ Domain / Aussie 的区级 unit 中位,注明口径。
- 可比优先级:同竖列(同平面同朝向)> 同楼同户型 > 同区同房数、建筑面积 ±20%、18 个月内;三项打分 = 面积与车位 / 楼层·朝向·景观 / 房况。`nsw_comps_enrich.py` 对 `<单元>/<门牌>` 地址跳过 L5,改从 `--building-json` 填。
- 「两房 ≤ 区 house 中位一半」只在该区独立屋年成交 ≥ 50 笔时用(North Sydney 每年 20–48 笔、单元占九成,规则没有判别力);硬信号改用楼内同户型 N 年自身增长(本例 2018 → 2026 ≈ +1 %/年)。
- 高层的 TOD / LMR 命中写「供应与景观遮挡」,不写「开发潜力」;`DA` 300 m 内 `COST_OF_DEVELOPMENT` ≥ $5M 的申请列表(地址、状态、造价、送件年)是景观遮挡的核心输入(`nsw_layers.py` v0.4 输出 `da_large`)。
- strata report / levies / 维修基金 / 缺陷 / cladding / 保险估值 = 付费或需人(固定口径 + slug);挂牌文案里的 Strata / Water / Council 三项支出可先写进 holding 标「中介自述」,等 s 184 证书核。

## 变更记录
- 2026-10-03:HAZ L1 Flood 只覆盖 10 个 LGA(实测 distinct LGA_NAME)。
- 2026-10-05:Northern Beaches council 服务接通;LMR 800 m 用步行路由。
- 2026-10-23(Salamander Bay 冷跑 Run 2 回写,v0.3):council 接口第二条路(ArcGIS Online / Experience Builder 反查)、Port Stephens 13 层接通、阳性/阴性对照取点法、全覆盖层只作旁注、Land Use Table 定位法、非住宅分区分支、洪水分档、去双重否定。
- 2026-10-28(North Sydney 高层 unit 冷跑 Run 4 回写,v0.4):§1 SP 四条实测(stratum 碎片、多 propid、L1 strata 稀疏、PCO_REF_KEY);§3 North Sydney 行(无 ArcGIS 洪水层,PDF + state_fallback 配置);§8 铁路隧道标记;「Unit 在 NSW 的补充」重写(Domain 楼栋页、可比优先级、house 中位规则适用条件、TOD 口径、strata 文件三档)。
- 2026-10-22(冷跑卡点回写):#3 SIXV L5 点查返回空 → 改 propid / address 属性查;#4 L4 弃用;#5/#6 Overpass 三镜像全挂 → TRANS L5 RoadSegment,只允许 outFields=* + distance;#7 DA_Tracking where 写法;#8/#9 legislation 官网 403 / Cloudflare → web.archive.org `id_` 快照,注意 gzip;#16 BOCSAR 下载抽取 + 全州基线;#17 公屋报 SAL+SA2;#18 AADT 进「要人做」;#21 CAD L9 取 Lot/DP。实例数据全部移入 `example-NSW.md`。
