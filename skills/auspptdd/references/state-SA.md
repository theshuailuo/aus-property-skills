
# auspptdd 州适配说明:South Australia (SA)

实测日期:2026-10-03。
- **主测试地址:10 Willcox Avenue, Prospect SA 5082**(干净的单户地块)。坐标 `lon=138.59543374 lat=-34.88467503`(SAGAF_Valuation 地理编码,score 100)。
- 对照地址:10 Gladstone Road, Prospect SA 5082(`lon=138.59251695 lat=-34.88355211`,score 100),用来演示"一块地多个估值号/多个产权"的识别。
- 全部为官方、免费、公开源:Location SA 地理编码器、SAPPA(South Australian Property and Planning Atlas)公共 MapServer、DIT 开放数据、PlanSA 官方页面。付费源(Land Services SA 的 SAILIS 查册、HtAG、CoreLogic)一律不用。

## 0. 通用约定(所有命令共用,先粘贴这段)

```bash
# 地理编码器(lsa1,免 Referer,实测可用)
GEO=https://lsa1.geohub.sa.gov.au/arcgis/rest/services/Locators
# SAPPA 主服务(lsa2)。⚠️ 必须带 Referer,否则 CloudFront 返回 403(实测:默认 curl、浏览器 UA 无 Referer 都 403,只加 Referer 即 200)
SAPPA=https://lsa2.geohub.sa.gov.au/arcgis/rest/services/SAPPA/PropertyPlanningAtlasV20/MapServer
REF="Referer: https://sappa.plan.sa.gov.au/"
# 点查:q_sa <图层号> [缓冲米数]   坐标替换 {lon} {lat}
q_sa(){ curl -s -H "$REF" -G "$SAPPA/$1/query" \
  --data-urlencode "geometry={lon},{lat}" --data-urlencode "geometryType=esriGeometryPoint" \
  --data-urlencode "inSR=4326" --data-urlencode "spatialRel=esriSpatialRelIntersects" \
  ${2:+--data-urlencode "distance=$2" --data-urlencode "units=esriSRUnit_Meter"} \
  --data-urlencode "outFields=*" --data-urlencode "returnGeometry=false" --data-urlencode "f=json"; }
```

- `features:[]` = 点不在多边形内。日期字段 epoch 毫秒:`1786579200000 = 2026-08-13`。
- 验证图层有数据:加第二个参数缓冲米数(`q_sa 141 2000`)。
- **关键存疑**:SAPPA 的 REST 是 SAPPA 网站自己用的公开端点,靠 Referer 才放行,**没有官方"开放 API"承诺,可能随时调整**。官方明确承诺的开放数据是 data.sa.gov.au 上的批量 GeoJSON/SHP(分区、叠加、细分区,每两周更新,CC BY)。skill 要稳定就把批量下载作后备(见各节 "后备")。
- 图层号来自 `$SAPPA?f=json` 目录(实测当天共 270+ 图层)。图层号会随版本变,按图层名找。

---

## 1. 地址 → 坐标 → 地块 → strata / community title

### 1.1 地址 → 坐标 + 估值号(官方,免费)
- 来源:Location SA(SA 政府)地理编码器 `SAGAF_Valuation`(带估值号版)与 `SAGAF_PLUS`。出处:https://lsa1.geohub.sa.gov.au/arcgis/rest/services/Locators 。SAPPA 前端也调用同一个 `SAGAF_Valuation`。

```bash
curl -s -G "$GEO/SAGAF_Valuation/GeocodeServer/findAddressCandidates" \
  --data-urlencode "Single Line Input={NUM} {STREET} {TYPE} {SUBURB} SA {POSTCODE}" \
  --data-urlencode "outSR=4326" --data-urlencode "maxLocations=1" --data-urlencode "outFields=*" --data-urlencode "f=json"
```
- ⚠️ **单行字段参数名就是 `Single Line Input`(带空格),写成 `SingleLine` 会 400/空**(`ALVS2CompositeSearch` 才用 `SingleLine`)。
- 读法:`candidates[0].score`(100=精确;**55 左右 = 找不到该门牌,退回到同名街的别的郊区,必须丢弃**——实测 "20 Devonshire Street Prospect" 返回 Hawthorn,score 55)、`location.x/y` = lon/lat、`attributes.Valuation`(10 位估值号/assessment number)、`SystemValuation`、`Ref_ID`。
- 实测 ✅:`10 WILLCOX AVENUE, PROSPECT, SOUTH AUSTRALIA, 5082`,score 100,`Valuation=0523521008`,`SystemValuation=112711`,坐标 138.59543374,-34.88467503。

### 1.2 地块(plan/parcel/title/面积/边界)
- 来源:SAPPA "Parcels Combined" 图层 41(含 `st_area(shape)` 面积)、"Land Parcels" 图层 269(含门牌、估值号、产权号)、"Valuation" 图层 43。

```bash
q_sa 41 ; q_sa 269 ; q_sa 43 ; q_sa 270      # 270 = Community(社区产权)
# 取边界:把 returnGeometry 改成 true,outSR=4326 即得多边形
```
- 读法(41):`plan_t`(平面类型:`F`=Filed Plan、`D`=Deposited Plan、`C`=Community Plan、`S`=Strata Plan、`H`/`G`/`R`/`T` 其他)、`plan`、`parcel_t`/`parcel`(`A`=Allotment 地块号;`U`=Unit,`CP`=Common Property)、`title_t/volume/folio`(产权 CT 卷/页)、`parcel_subtype`(`AL`=普通地块,`UN`/`UC`=strata 单元/公共地,`FL` 等)、`st_area(shape)`=面积(m²,与周长 200 m 量级一致)。
- 读法(269):`valnno`估值号(一个地块可有多个)、`unit_no`、`house_no`、`title_ref`(CT 卷/页)、`hundred`。
- 实测 ✅ **主地址 Willcox**:`F109732 A67`(Filed Plan 109732,Allotment 67),`CT5530/138`,`parcel_subtype=AL`,**面积 1,839.9 m²**,周长 200.6 m,`valnno=0523521008`,`hundred=YATALA`;`Community`(270)0 命中 → **非 strata、非 community title,标准 Torrens 单户地块**。
- 实测 ✅ **对照 Gladstone**:单点返回 12 行,`D850 A9`(Deposited Plan 850,Allotment 9),4 个不同估值号(`0525888997` 无 unit、`0525889009` unit 1、`052589000*` unit 2、`0525891002` unit 3),产权 `CT6126/122、/123、/124`,地块面积 1,213.3 m²,41 层 `qualifier=+titles`。**一块地多个估值号+多个 CT = 多户/单元式占用,不是单户**,尽调要按"分户/共有"处理(Gladstone 的 plan_t=D、不是 S/C,所以不是正式 strata,可能是共有产权或多栋同地块,须看 Certificate of Title)。
- strata/community 判断口径(已实测查到样例):`plan_t='S'`(如 S1001 UC CP、S1034 UN 4)= strata;`plan_t='C'`(如 C25327 FL4)= community plan;图层 270 命中 = 社区产权。`plan_t='U'` 在 Prospect 1.5 km 内未查到样例,**未实测**。

---

## 2. 规划分区 + 叠加层 + 技术数字变量 + 遗产

### 2.1 Planning and Design Code Zone
- 来源:SAPPA "Planning and Design Code > Zones" 各大类图层(392 Activity、394 Capital City、393 Employment、395 Infrastructure、396 Natural Resources and Environment、**397 Neighbourhood and Corridor**、398 Rural、399 Township and Settlement、400 Tourism),Subzones 404–412,另有 243 "P&D Code Subzoning"。批量数据集:https://data.sa.gov.au/data/dataset/planning-and-design-code-zones (SHP/GeoJSON/KML,CC BY,Housing and Urban Development)。

```bash
for L in 392 394 393 395 396 397 398 399 400; do echo "== $L"; q_sa $L; done          # 只有一个会命中
for L in 404 405 406 407 408 409 410 411 412 243; do echo "== sub $L"; q_sa $L; done   # 细分区
```
- 也可用一次 identify 取多层(已实测):

```bash
curl -s -H "$REF" -G "$SAPPA/identify" --data-urlencode "geometry={lon},{lat}" --data-urlencode "geometryType=esriGeometryPoint" \
 --data-urlencode "sr=4326" --data-urlencode "layers=all:397,129,141,372,403,135,136,137,140,133,143,145,146,147,148" --data-urlencode "tolerance=1" \
 --data-urlencode "mapExtent={lon-0.001},{lat-0.001},{lon+0.001},{lat+0.001}" --data-urlencode "imageDisplay=400,400,96" --data-urlencode "returnGeometry=false" --data-urlencode "f=json"
# 注意 mapExtent 里的算式要先自己算成数字;实测只回了有命中的层(zone 397 + Character Area 129)
```
- 读法:`name`(分区全称)、`value`(缩写,如 EN)、`id`(Code 内部 ID)。
- 实测 ✅ Willcox:`name=Established Neighbourhood`,`value=EN`,`id=Z1506`;其余各类分区/细分区 0 命中。
- 后备(批量):`https://www.dptiapps.com.au/dataportal/PDCodeZones_geojson.zip`(官方开放数据,未下载)。

### 2.2 Overlays(叠加层,SAPPA 已拆成单独图层)
实测在 Willcox 命中的叠加层:

| 图层 | 名称 | 返回 | 含义 |
|---|---|---|---|
| 129 | Character Area Overlay | `id=O0901, value=PrC1, legalstartdate=2026-08-13` | 位于特征区(要保留街景特征,拆除/新建/加建受限) |
| 152 | Airport Building Heights (Regulated) | `value=All structures over 45 metres` | 仅超过 45 m 的结构受限,低层住宅无影响 |
| 164 | Traffic Generating Development | — | 与干道交通生成开发相关,住宅一般无影响 |
| 360 | Stormwater Management | `legalstartdate=2026-08-13` | 新开发须做雨水收集/WSUD |
| 361 | Urban Tree Canopy | `legalstartdate=2026-08-13` | 须种/留树 |
| 174 | Regulated and Significant Tree | `legalstartdate=2021-08-26` | 受管制/重要树木,砍树须批 |

另测 **0 命中**:128 Affordable Housing、130 Design、131 Gateway、442 Co-located Housing、448 Significant Retirement Facility…、143 Historic Area、145 Heritage Adjacency、146 Local Heritage Place、147 State Heritage Area、148 State Heritage Place、366 Future Local Road Widening、158 Future Road Widening、157、159、161、162、163、165、173/175/176 植被、367 Coastal Flooding。

### 2.3 技术与数字变量(TNV,小地块/限高/覆盖率关键)
Willcox 在 TNV 图层的命中(直接可读的 `description`,`legalstartdate=2026-08-13`):

| 图层 | 变量 | 描述 |
|---|---|---|
| 206 | Minimum Site Area | detached/semi-detached/row/group/residential flat 均为 **560 sqm** |
| 205 | Minimum Frontage | 以上各类型均 **15 m** |
| 202 / 203 | Maximum Building Height | **9 m / 2 层** |
| 353 | Minimum Side Boundary Setback | **1 m(首层);3 m(二层及以上)** |
| 354 | Site Coverage | 最大 **50%** |

- 读法:`description` 直接是中文可转述的自然语言;`value` 是数值。**这就是 SA 的"地块能否拆分"判据**:地块面积 ÷ 最小地块面积、frontage ≥ 最小面宽。Willcox 1,839.9 m² ≈ 3.3 倍 560 m²,frontage 须实测(可由多边形算最短临街边)才能判断能否分 3 块。
- 0 命中:204 Minimum Dwelling Allotment Size、352 Primary Street Setback、369 Rear Setback、349 Building Envelope。

### 2.4 Heritage
- 图层 146 Local Heritage Place、148 State Heritage Place、147 State Heritage Area、143 Historic Area Overlay、145 Heritage Adjacency;另有 Planning Reference > Heritage 下 SA Heritage Sites(212/213)、State Heritage Areas(214)、Commonwealth(424)、National(423)。
- 实测 ✅ Willcox:四个遗产叠加层点上均 0;**但在 500 m 内:State Heritage Place 1、Local Heritage Place 36、Historic Area 3、Heritage Adjacency 21**(`q_sa 146 500` 等)——区域遗产很密。Willcox 本身只有 **Character Area**(非遗产)。
- 判读:Character Area/Historic Area 对拆除重建、外观改动影响大,但与 Local/State Heritage Place 法律层级不同;邻近遗产 (Heritage Adjacency) 影响的是建筑形态审批。

---

## 3. 洪水

- SAPPA 叠加层:**141 Hazards (Flooding)(原名 Flooding High)**、**372 Hazards (Flooding - General)**、**403 Hazards (Flooding Evidence Required)**、367 Coastal Flooding。名称来自 Code Overlay O2403/O2414。

```bash
for L in 141 372 403 367; do echo "== $L"; q_sa $L; done
for L in 141 372 403; do q_sa $L 500 | python -c "import sys,json;print($L,len(json.load(sys.stdin).get('features',[])))"; done
```
- 读法:命中即该 Code 叠加层触发,开发评估要求地面/地板标高(见 TNV 图层 201 Finished Ground and Floor Levels)与洪水评估。高风险 141 的触发强于 372。
- 实测 ✅ Willcox:**三个洪水层点上均 0**;缓冲数据验证:500 m 内 141=2、372=155、403=0;2 km 内 141=150、372=1,039。→ 本地块不在洪水叠加层,但周边 General 层密集,**需查议会洪水图**。
- 抽样验证:取 500 m 内 372 / 141 的真实多边形顶点点查,各返回 1 命中(证明层可用)。
- ⚠️ 判读限制:Code 洪水叠加层是全州统一模型的简化,**议会洪水图/排水研究更准**(Prospect 归 City of Prospect);"State-Wide Flood Hazard Code Amendment" 正在征询(搜索摘要提到咨询截止 2026-08-13,**未读官方原文,存疑**),规则可能变。人工入口:council 洪水地图 + SAPPA 页面 https://sappa.plan.sa.gov.au/ 。

---

## 4. 山火

- SAPPA 叠加层:135 Hazards (Bushfire - High Risk)、136 Medium Risk、137 General Risk、140 Urban Interface、138 Outback、139 Regional。

```bash
for L in 135 136 137 138 139 140; do echo "== $L"; q_sa $L; done
```
- 读法:High > Medium > General;Urban Interface 在城市边缘草林交界。命中会触发 BAL 评估与 CFS 参考。
- 实测 ✅ Willcox:六个层点上均 0;缓冲:2 km 内 0,10 km 内 135/136/140 各 1(在 Adelaide Hills/Torrens 峡谷一带)。→ 无山火叠加层。
- 判读:City 城区住宅一般不触发;山坡/Hills 地块要看。

---

## 5. 滑坡 / 酸性硫酸盐土 / 污染场地 / 其它

| 项 | 来源与图层 | 实测(Willcox) |
|---|---|---|
| 酸性硫酸盐土 | SAPPA 133 Hazards (Acid Sulfate Soils) | ✅ 0 命中(10 km 内仅 1 处,沿海区) |
| 地震 | SAPPA 252 Earthquake Hazard Zones(Referral Layers) | ✅ 命中:`acceleration_coefficient <= 0.11`,"hazard factor (Z) of 0.11 or less",供 AS 1170.4 家居结构设计 |
| 腐蚀环境 | SAPPA 254 Corrosion Protection Environments | ✅ 0 命中 |
| 能效分区 | SAPPA 255 Energy Efficient Zones | ✅ `Zone 5, Warm temperate`(建筑能效规定气候区) |
| 活跃/反应性土 | SAPPA 58 Type B PU Reactive Soil | ✅ 0 命中,2 km 内 0(这层覆盖有限,**无命中≠无反应土**,新建房基础仍做岩土报告) |
| 污染场地 | SAPPA 380 Section 83A Notification、371 Groundwater Prohibition Area;EPA 公共登记册 https://epa.sa.gov.au/public_register/site_contamination_index (按郊区/议会浏览) | ✅ 380、371 点上 0;EPA 登记册为网页,**⚠️ 需浏览器人工**(搜索摘要可见,未实测) |
| 滑坡 | 未发现 SAPPA/DIT 公共滑坡图层(**未实测**) | ⚠️ 阿德莱德平原地块基本不涉及;Hills 需人工 |
| 机场噪声 | SAPPA 153 Aircraft Noise Exposure、425 Aircraft Noise Reduction | ✅ 点上均 0;2 km 内 153=2、425=2(最近 ≈ 周边 2 km 内) |

---

## 6. 官方估价

- 来源核查:SA Valuer-General(估值日 1 Jan,每年 7/1 生效)。官方页 https://valuergeneral.sa.gov.au/valuation/Property-Valuations (页面更新 2025-08-05)原文:找估值的途径是 "Statutory authority notices such as council rates, water and sewerage rates or Emergency Services Levy and land tax"、"South Australian Land Information System (SAILIS)"、"Contact Land Services SA via telephone on 1300 653 346"。
- ❌ **无免费逐地块站点值/资本值 API**。SAILIS(Land Services SA)是按次收费的产品,按硬约束不使用。
- ✅ **能免费拿到的只有"估值号"**:地理编码器 `SAGAF_Valuation` 返回 `Valuation`(10 位);SAPPA 图层 43/269 也给 `valuation_no`/`valnno`。拿到估值号后,客户用它去 council/SA Water/ESL 单据或 SAILIS 自查价格。
- 实测 ✅ Willcox:`valuation_no=0523521008`,`property_location="10 WILLCOX AV PROSPECT SA 5082 LT 67 F109732"`。
- 报告写法:"SA 官方估值(Site/Capital Value)须付费 SAILIS 或看 rates notice;本报告只附估值号,价格用可比成交/AVM。"

---

## 7. DA / 开发活动公开接口

- ✅ SAPPA 图层 240 "Development Applications - PDI Act" 和 241 "Development Applications - Dev Act"(旧法)。

```bash
q_sa 240        # 命中 = 该地块上登记过的 DA(多边形=地块)
q_sa 240 300    # 300 m 周边 DA(注意会返回很多条,可加 resultRecordCount=50)
q_sa 241
```
- 读法(240):`applicationid`、`lodgementdate`(epoch ms)、`applicationstatus`(Decision Made 等)、`natureofdevelopment`、`applicationurl`(PlanSA DA 登记册详情页);(241)另有 `developmentnumber`、`decision`、`description`、`decisiondate`。
- 实测 ✅ Willcox(PDI Act)命中 2 条:`25034924`,lodged 2025-11-12,"Additions and Alterations to Existing Dwelling",Decision Made;`24027158`,lodged 2024-10-30,"Outbuilding (Garage)",Decision Made;`applicationurl` 形如 `https://plan.sa.gov.au/development_application_register#view-25034924-DAP`。旧法层 241 点上 0。
- 判读:这是**地块上的历史/在审 DA**(可看出业主做过哪些改造、是否有非法加建线索),也可对周边 300–500 m 做缓冲统计在建/新批项目。数据只含 PDI Act(2020 年后)+ Dev Act 遗留。**详情文档**需访问 `applicationurl`(⚠️ plan.sa.gov.au 对 curl 返回 Cloudflare 挑战,需浏览器)。
- 另有 235–239 EDALA 土地分割(Land Division Deposits/Proposals/Refused/Lapsed/Withdrawn)图层,可查分割申请,**未实测命中**。

---

## 8. 道路车流量 / 铁路 / 机场

### 8.1 DIT Traffic Volumes(官方开放数据)
- 来源:SA DIT"Traffic Volumes"(AADT 双向估算,每年更新)。数据集:https://data.sa.gov.au/data/dataset/traffic-volumes ;数据页更新 2026-09-24;2026 版 GeoJSON(2.1 MB,免登录):
  `https://data.sa.gov.au/data/dataset/e5d6588a-f163-4f6a-bc57-25e95c87b5bd/resource/f6800eea-b0c2-45d9-a010-ba7cc22b0ee7/download/trafficvolumeestimates2026_geojson.zip`
- **没有在线 REST 查询**(已找:DIT geohub 的 RoadAsset/Transport/Hosted 目录无 traffic volume 服务,`State_Maintained_Road_Network` 只有 `traffic_score`)。做法=下载 zip → 本地按最近路段查。坐标系是 **EPSG:3107**,要先把 `{lon},{lat}` 投影成 3107:

```bash
# 1) 投影(官方 Geometry 服务,免 Referer)
curl -s -G "https://dpti.geohub.sa.gov.au/server/rest/services/Utilities/Geometry/GeometryServer/project" \
  --data-urlencode "inSR=4326" --data-urlencode "outSR=3107" \
  --data-urlencode 'geometries={"geometryType":"esriGeometryPoint","geometries":[{"x":{lon},"y":{lat}}]}' --data-urlencode "f=json"
# 2) 本地:对 geojson 每条 LineString 算到该点的最近距离,取最近 5 条
# 3) 路名:用 ROAD_NO 查 State_Maintained_Roads(FeatureServer/0)
curl -s -G "https://dpti.geohub.sa.gov.au/server/rest/services/Hosted/State_Maintained_Roads/FeatureServer/0/query" \
  --data-urlencode "where=crrs_road_no='{ROAD_NO}'" --data-urlencode "outFields=rdname,functional_class,speed_limit,road_class" \
  --data-urlencode "returnGeometry=false" --data-urlencode "resultRecordCount=1" --data-urlencode "f=json"
```
- 读法:`TESECN_VOLUME`=AADT 估算;`TESECN_BASE_YEAR`=实测基准年,`TESECN_PROJECTED_YEAR`=推算年;`CV_PERCENT`/`NUMBER_CVS`=商用车比例/数量;`ROAD_NO` 对应 DIT 道路号。
- 实测 ✅ Willcox(2026 文件,共 2,721 段):最近 **PROSPECT RD(ROAD_NO 05627)140 m,17,400 辆/日(基准年 2022),CV 3.5%(590)**;279 m 另一段 14,400;673 m **MAIN NORTH RD(05610)42,000(2022/2023 推算)**。
- 判读:基准年多为 2022,不是当年实测;只覆盖州管干道,本地街(Willcox Ave)无数据。

### 8.2 铁路
- 来源:DIT geohub `Hosted/Railway_and_Tram_Lines_in_South_Australia_WFL1/FeatureServer/1`(Railway)。

```bash
curl -s -G "https://dpti.geohub.sa.gov.au/server/rest/services/Hosted/Railway_and_Tram_Lines_in_South_Australia_WFL1/FeatureServer/1/query" \
 --data-urlencode "geometry={lon},{lat}" --data-urlencode "geometryType=esriGeometryPoint" --data-urlencode "inSR=4326" \
 --data-urlencode "spatialRel=esriSpatialRelIntersects" --data-urlencode "distance=2000" --data-urlencode "units=esriSRUnit_Meter" \
 --data-urlencode "outFields=track_name,track_gauge,status,track_ownership" --data-urlencode "returnGeometry=false" --data-urlencode "f=json"
```
- 实测 ✅:200/500/1000 m 内 0;2 km 内命中 `track_name=GAWLER LINE, track_gauge=BROAD, status=Operational, track_ownership=KEOLIS DOWNER PTY LTD`;二分查得最近约 **1,109 m(±25)**。
- 附:SAPPA 图层 159 Key Railway Crossings(点上 0,2 km 内 1)、162 Noise and Air Emissions(点上 0,500 m 内 1)。

### 8.3 机场 / ANEF
- SAPPA 153 Aircraft Noise Exposure(Code 里的机场噪声叠加层,取代 ANEF 等值线用于规划)、425 Aircraft Noise Reduction(Building Code 层)、152 Airport Building Heights(Regulated)。
- 实测 ✅ Willcox:153、425 点上 0;152 命中(只管 45 m 以上结构)。
- ⚠️ 原始 ANEF 等值线图没有免费 REST,Adelaide Airport 以其总体规划 PDF 为准(人工)。

---

## 9. 政策红利(只引官方原文+日期)

1. **自带出租**:PlanSA 新闻(发布 **2023-11-27**):"Amended regulations now ensure all existing ancillary accommodation can be leased or rented out";"it is no longer an offence to enter into an agreement to rent a granny flat with anyone, even if development approval limits use or restricts occupation to family of the main home's residents."——出处 https://plan.sa.gov.au/news/article/2023/new-planning-rules-secure-granny-flats-for-rental-and-boost-design-for-new-homes (浏览器读取)。
2. **自成一户(self-contained)的 granny flat**:PlanSA 新闻(发布 **2024-03-04**):"From today, councils will have greater powers to approve self-contained accommodation";当时 Ancillary Accommodation and Student Accommodation Definitions Review Code Amendment 在征询至 15 April,议会可先"on an interim basis"执行——出处 https://plan.sa.gov.au/news/article/2024/reducing-red-tape-to-create-more-housing-options 。**Code Amendment 正式生效日期未能从官方原文核实**(搜索摘要有"2024-11-18 部长通过"的说法,与"2024-03-04 早期执行"并存,**存疑,不写入判读**)。
3. **granny flat 是否要批**:PlanSA 2023 页只说"streamlining the approval pathway…being considered";议会页(Onkaparinga,二手)称 ancillary accommodation 仍需 DA。**官方免批豁免条款未找到**——不要像 WA 那样写"免规划批准"。
4. **Future Living Code Amendment**(共居/联排的新用地定义):Part 1 由部长于 **2025-04-26** 通过(引自 SA 政府 YourSay 页,2026-10-03 经 engagementhq 镜像读取;Part 2 生效日期该页未给),内容含 "new land use definition, new Co-located Housing Overlay, and amendments to the Established Neighbourhood Zone, overlays and general development policies";Part 2 决定 Overlay 落在哪些议会的 Established Neighbourhood Zone。SAPPA 已有图层 442 **Co-located Housing**,**Willcox 点上 0 命中**(此处不适用)。
5. **小地块**:SA Code 的小地块规则以 TNV 层给出(见 2.3):Willcox 所在 Established Neighbourhood 最小地块面积 560 m²、最小面宽 15 m。其它分区(如 General Neighbourhood、Urban Renewal)数值不同,按各点读取 TNV 层,不凭记忆写。
6. 全部 TNV/overlay 属性里的 `legalstartdate`(本次读到的 2026-08-13)是该条 Code 现行版本起始日,报告里需写"据 SAPPA 2026-10-03 读取,Code 条目现行起始 2026-08-13"。

---

## 10. 测试地址实测结果汇总表(10 Willcox Avenue, Prospect SA 5082)

| # | 检查项 | 状态 | 关键返回 |
|---|---|---|---|
| 1a | 地址→坐标 | ✅ | score 100,138.59543,-34.88468;估值号 0523521008 |
| 1b | 地块/面积/产权 | ✅ | F109732 A67,CT5530/138,1,839.9 m²,周长 200.6 m |
| 1c | strata / community | ✅ 否 | plan_t=F,community 层 0;对照地址 Gladstone 是多估值号共地块 |
| 2a | Zone | ✅ | Established Neighbourhood(EN) |
| 2b | Overlays | ✅ | Character Area(PrC1)、Stormwater、Urban Tree Canopy、Regulated Tree、Airport Heights(>45 m)、Traffic Generating |
| 2c | TNV | ✅ | 最小地块 560 m²、面宽 15 m、高 9 m/2 层、覆盖率 50%、侧退线 1/3 m |
| 2d | 遗产 | ✅ 点上无 | 500 m 内 State Place 1、Local Place 36、Historic Area 3 |
| 3 | 洪水 | ✅ 点上无 | 500 m 内 High 2/General 155;需查议会洪水图 |
| 4 | 山火 | ✅ 无 | 2 km 内 0 |
| 5 | ASS/地震/污染 | ✅ | ASS 0;地震 Z≤0.11;83A/地下水禁用区 0 |
| 6 | 官方估价 | ❌ 价格 / ✅ 估值号 | Valuer-General 数据须 SAILIS(付费)或 rates notice |
| 7 | DA | ✅ | PDI Act 2 条:2025-11-12 加建(已批)、2024-10-30 车库(已批) |
| 8a | 车流量 | ✅ | Prospect Rd 17,400/日(基准 2022,CV 3.5%,140 m) |
| 8b | 铁路 | ✅ | Gawler Line 约 1,109 m |
| 8c | 机场 | ✅ | 噪声层不命中;高度层仅 >45 m |
| 9 | 政策红利 | ✅ 官方原文 | 2023-11-27 可出租;2024-03-04 自成一户 interim;TNV 560 m² |

## 11. 未解决 / 存疑清单

1. **Referer 依赖**:SAPPA lsa2 必须带 `Referer: https://sappa.plan.sa.gov.au/` 才返回 200,否则 CloudFront 403。这是 SAPPA 网站自用的公开端点,**非官方开放 API 承诺**;稳定后备 = data.sa.gov.au 批量下载(PDCodeZones/Overlays/SubZones GeoJSON,每两周更新);一旦端点封堵 skill 要降级为"人工看 SAPPA 页面 https://sappa.plan.sa.gov.au/ ,或用批量数据离线点查"。
2. SA **逐地块 Site/Capital Value**:无免费接口;SAILIS(付费)。仅能拿估值号。
3. **DA 详情**(`applicationurl`)需浏览器(plan.sa.gov.au 对 curl 返回 Cloudflare 挑战);用图层 240/241 只能拿到列表字段。
4. **Traffic Volumes** 无在线 REST,需下载 2.1 MB geojson 并从 EPSG:3107 做最近路段计算;基准年多为 2022。
5. **Ancillary Accommodation Code Amendment 正式生效日期**和 granny flat 现行免批规则未核实(2024-03-04 的是 interim);勿写"免批"。
6. **State-Wide Flood Hazard Code Amendment** 仅从搜索摘要得知有咨询,**未读官方原文**。
7. **plan_t='U'(Unit Plan)** 前缀在样例范围内未查到,strata 以 `S` 前缀为准,**其他州式前缀未实测**。
8. 图层号/名称随 SAPPA 版本(PropertyPlanningAtlasV20)变化;图层 442 Co-located Housing 只验证了存在与 Willcox 0 命中。
9. 本次读到的 Code `legalstartdate=2026-08-13`(多个叠加层/TNV 同日),对应哪次 Code Amendment **未核实**。
10. EPA 污染登记册、原始 ANEF、议会洪水图均为网页/PDF,需浏览器人工。
11. 滑坡风险无公共图层(平原地块不涉及)。
