# auspptdd 州适配说明:Western Australia (WA)

实测日期:2026-10-03(独立屋)、2026-10-27(strata unit)。测试地址:**22 Burnley St, Thornlie WA 6108**(City of Gosnells,Torrens 独立屋)与 **18/90 Terrace Road, East Perth WA 6004**(City of Perth,115 户 strata 公寓;unit 实测表见 §10b)。
测试坐标(取自 Landgate 地籍地址多边形顶点平均,WGS84):Thornlie `lon=115.96552  lat=-32.05638`。
全部为官方、免费、公开、免登录源(Landgate SLIP Public Services、DWER、DPLH、Main Roads WA)。付费源(Landgate 估值摘录、产权查册、HtAG、CoreLogic)一律不用。

## 0. 通用约定(所有命令共用,先粘贴这段)

```bash
# SLIP 公共 ArcGIS 根;免登录,curl 直接可打(无需 Referer/UA)
SLIP=https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services
# 点查:q_wa <服务名> <图层号> [缓冲米数]   坐标在命令里替换 {lon} {lat}
q_wa(){ curl -s -G "$SLIP/$1/MapServer/$2/query" \
  --data-urlencode "geometry={lon},{lat}" --data-urlencode "geometryType=esriGeometryPoint" \
  --data-urlencode "inSR=4326" --data-urlencode "spatialRel=esriSpatialRelIntersects" \
  ${3:+--data-urlencode "distance=$3" --data-urlencode "units=esriSRUnit_Meter"} \
  --data-urlencode "outFields=*" --data-urlencode "returnGeometry=false" --data-urlencode "f=json"; }
```

- 返回 `features:[]` = 该点不在任何多边形内(命中即有一条 `attributes`)。
- 日期字段(`gazettal_d`、`designationdate` 等)是 epoch 毫秒,换算:`1759190400000 = 2025-09-30`。
- 要核对"图层是否真有数据"(防止空图层误判为无风险):加第三个参数缓冲米数,例如 `q_wa Water 21 3000`。
- SLIP 图层号会随版本增删。图层名称带括号编号(如 `DPLH-071`)是稳定的数据集 ID,图层号变了就按 ID 去 `.../MapServer?f=json` 里找。

---

## 1. 地址 → 坐标 → 地块 → 是否 strata

### 1.1 地址 → 地块多边形(官方,免费)
- 来源:Landgate "Cadastre Address (LGATE-002)",SLIP `Places_and_Addresses/MapServer/4`(Large Scale;小比例尺为图层 3)。
  出处:https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Places_and_Addresses/MapServer ;目录页 https://catalogue.data.wa.gov.au
- 没有 geocoder(`Locate` 服务不是地址编码器,已实测 `find` 返回空)。做法是直接按字段筛地址多边形,**road_number_1 是字符串必须加引号**(写数字会 400):

```bash
curl -s -G "$SLIP/Places_and_Addresses/MapServer/4/query" \
  --data-urlencode "where=road_name='{STREET_UPPER}' AND road_type='{TYPE_ABBR}' AND locality='{SUBURB_UPPER}' AND road_number_1='{NUM}'" \
  --data-urlencode "outFields=*" --data-urlencode "returnGeometry=true" --data-urlencode "outSR=4326" --data-urlencode "f=json"
# 例:STREET=BURNLEY TYPE=ST SUBURB=THORNLIE NUM=22
```
- 读法:`features[0].geometry.rings[0]` 取顶点平均 = 坐标 `{lon},{lat}`;`attributes.land_id` = Landgate Land ID;`lot_number` 对"门牌式地址"是 null(见下);单元式地址会有 `road_number_2`/`lot_number`。
- 备选(未作为主路径):OSM Nominatim 仅返回到街道级(实测 22 Burnley St 只回街道中点,无门牌),不可靠,只当兜底。
- 实测 ✅ 返回:`land_id=1505172`,`road_number_1=22 BURNLEY ST THORNLIE`,`view_scale=4K`,环 8 个顶点,中心 `115.96552, -32.05638`。

### 1.2 面积 / 边界
- 官方免费源**没有面积字段**。从 1.1 返回的多边形自己算(把经纬度换成米后用鞋带公式)。
- 实测:约 **804 m²**(自算,±1%,边长约 19.1 m 宽、纵深约 42 m,一角切角)。官方法定面积只在 Certificate of Title / 地块平面图(Landgate 付费查册),所以报告里写"自算约 X m²,以产权为准"。
- 取边界 GeoJSON:同命令加 `f=geojson`。

### 1.3 Plan / Lot 编号与 strata 判断
- 来源:Landgate "Plan Extent (LGATE-284)",`Property_and_Planning/MapServer/135`。

```bash
q_wa Property_and_Planning 135
```
- 读法:`plan_identifier`(如 `P00008818`)、`label_text`(`P    8818`)。**前缀 = 平面类型:`P`=Deposited Plan 普通地块;`D`=Diagram;`SP`=Strata Plan(分层产权)**。`SP`/`D`/`P` 已用 `where=plan_identifier LIKE 'SP%'` 实测各取到样例(SP00000045 等)。`CP`(Survey-Strata / Community)前缀未测到样例,**未实测**。
- 实测 ✅:22 Burnley St → `plan_identifier=P00008818`(Plan 8818,1960 年代老 plan),`status=Integrated`,**非 strata**。单点只返回 1 个 plan 多边形、地址多边形也只有 1 个,与"独立 Torrens 地块"一致。
- ⚠️ Lot 号:`Cadastre Address` 对门牌地址 `lot_number=null`,Plan Extent 也无 lot。**免费源拿不到 "Lot X on Plan 8818"**,要确切 lot 需 Landgate 产权查册(付费)或让客户给 Certificate of Title / 地税单。
- 判读注意:strata 地块多边形很小且多个 lot 叠在同一 plan 上(`SP` 前缀 plan 下按楼层/单元切成多块);点查若同时返回多个重叠地址多边形也是提示信号。

### 1.4 Unit 怎么识别(2026-10-27 East Perth 实测)
- **Cadastre Address(LGATE-002)没有单元级记录**:90 Terrace Rd 只有 1 条 `road_number_type='H'` 的母地址;按 `road_number_2='90'` 查单元返回 0;Large Scale 图层 2 对 `where` 查询返回 400(只接受几何查询)。**单元号只能从挂牌页来**(Aussie / Domain / REA)。
- Plan Extent(图层 135)同一点返回 **3 个 plan 叠放**(D 12226、DP 63152、SP 58159):历史 D / DP 与现行 SP 叠放是改建地块的常态,**取 SP**;`SP` 前缀即 strata。
- `Property_and_Planning/MapServer/2`(Cadastre No Attributes,LGATE-001)同点返回 **116 个叠放多边形 = 115 个 strata lot + 共用部分**,可用来数户数、核对中介文案里的「Total Strata Lots」。
- 地块面积字段对 unit 无意义:Aussie 页的「land」是 **strata lot 总面积**(含阳台/车位/储物,本例 187 m²,室内 136 m²),报告写「strata lot 187 m²(室内 136)」,不写「土地」。
- Lot 号:按单元号推定(Lot 18 ≈ 单元 18)并注明「未经产权核对」;确切 lot 看 Certificate of Title / strata plan 副本(§6b)。

---

## 2. 规划分区 + 叠加 + 密度码 + 遗产

### 2.1 Local Planning Scheme 分区(zone)
- 来源:DPLH "Local Planning Scheme - Zones and Reserves (DPLH-071)",`Property_and_Planning/MapServer/112`。目录:https://catalogue.data.wa.gov.au/dataset/local-planning-scheme-zones-and-reserves-dplh-071

```bash
q_wa Property_and_Planning 112
```
- 读法:`zone`(Residential/Mixed Use/Commercial…)、`lga`、`scheme_nam`、`gazettal_d`(方案刊宪日)、`rest_label`/`special_la`(限制/特别用途标签,空格=无)。
- 实测 ✅:`zone=Residential`,`lga=City of Gosnells`,`scheme_nam=GOSNELLS`,`scheme_no=24`,`gazettal_d=1759190400000`(2025-09-30)。

### 2.2 R-Codes 密度码
- 来源:DPLH "Local Planning Scheme - R Codes (DPLH-070)",图层 111。

```bash
q_wa Property_and_Planning 111
```
- 读法:`rcode_no`(如 R40)。**R 码是"代码",具体最小/平均地块面积、退线、容积率要查 R-Codes Vol 1 表格**(见第 9 节;本说明不引用未核对的数值)。
- 实测 ✅:`rcode_no=R40`(Gosnells 方案 24)。→ 22 Burnley St 为 R40 住宅区,地块约 804 m²,是 WA 里"可拆分/加盖"的典型候选,具体能否分块要按 Vol 1 R40 面积表和本地方案条款核。
- ⚠️ 判读:有些 LPS 对同一地块还有"地方规划政策/结构规划/特别用途区"。图层 109(LPS Special Area)、32(Structure Plan Boundaries)已测,本点无命中。

### 2.3 都会区域规划(MRS)
- 图层 48(Region Scheme - Zones and Reserves,DPLH-023)。实测 ✅:`descriptio=Urban`,`reg_scheme=MRS`,`rs_class=Zone`。
- 若返回是 Reserve(如 Parks and Recreation / Primary Regional Roads)则土地可能被征收/限制,需人工复核。

### 2.4 Heritage
- 来源:`People_and_Society` 服务。已实测可用图层:
  - 7 Heritage Council WA - State Register (DPLH-006)
  - 16 Heritage List (DPLH-090)
  - 9 Heritage Council WA - Local Heritage Survey (DPLH-008)
  - 15 Heritage Areas (DPLH-089)
  - 17/18/19 Aboriginal Cultural Heritage (Historic/Register/Lodged)(未实测)

```bash
for L in 7 16 9 15; do echo "== $L"; q_wa People_and_Society $L; done
q_wa People_and_Society 9 300   # 300 m 内有没有本地遗产调查点(判断邻居效应)
```
- 读法:命中则读 `place_name`、`more_info`(inHerit 链接 https://inherit.dplh.wa.gov.au/public/p/{place_no})。
- 实测 ✅:点上 4 个图层均 0 命中(不是遗产保护地块);300 m 内 Local Heritage Survey 有 3 处(Crestwood Estate cluster、Thornlie Square Shopping Centre、Thornlie Child Health Centre),只是邻近。
- 判读:Local Heritage Survey ≠ 法定保护,仅是调查名单;State Register 才有法律约束。WA 没有 NSW 式"conservation area overlay",老街区保护要看 LPS 文本里的 Heritage Area/特别控制区(图层 15、LPS 109)。

---

## 3. 洪水

### 3.1 DWER Floodplain Management(Perth 主要河流)
- 来源:DWER FPM,SLIP `Water/MapServer`。已实测图层:8 FPM Extent of Flooding(DWER-017);21 FPM Floodplain Area(DWER-020);23 Floodway and Flood Fringe Area(DWER-014);54 1% AEP Floodplain Development Control Area(DWER-003,**由洪泛范围外扩 300 m 派生**);0 Flood Level Points(m AHD);11 Flood Level Contours。

```bash
for L in 8 21 23 54; do echo "== $L"; q_wa Water $L; done
q_wa Water 54 3000   # 缓冲查,确认图层有数据
```
- 读法:命中则读 `ext_type`(如 `1 in 10 (10%) AEP floodplain`,另有 1% AEP 等)、`hyd_name`(河名)、`fpm`、`source`/`date_check`(数据日期)。`Flood Level Points/Contours` 给 m AHD 洪水位,可与地块高程(未测高程源)比。
- 实测 ✅:点 **不在** 任何 FPM 图层内;最近 FPM 洪泛范围 ≈565 m,最近 DCA(300 m 缓冲)≈273 m(Canning River and tributaries);DCA 命中记录 `name=Canning River and tributaries (Upstream of Canning Bridge) - Perth`。
- 判读:FPM **只覆盖做过洪水研究的河道洪泛区**;没命中时写「未检出 · 下一步:council 洪水/排水信息」(不写双重否定);市政排水/内涝/Thornlie 内部沟渠不在内。要补:City of Gosnells 洪水/排水信息、Water Corporation 排水(`Infrastructure_and_Utilities` 图层 81 Declared Drainage Areas,Thornlie 无命中)。
- **分档(对应 SKILL.md「Flood is tiered」)**:Extent of Flooding(8)或 Floodway(23)命中 = 否决级;Floodplain Area(21)或 DCA(54,洪泛外扩 300 m)命中而 Extent 未命中 = **条件项**(`status: cond`),固定两条下一步;全部未命中 = 未检出。公寓非地面层:条件项的两条下一步改成「地下车库与地面层高程 vs 规划洪水位」「strata 保单含洪水 + 两家报价」。
- Flood Level Points(图层 0,DWER-019)字段:`fldlvl_10 / fldlvl_100 / fldlvl_dfe / fldlvl_pmf`(m AHD),`-9999` = 无值;`fldlvl_dfe` 元数据原文「1% AEP + sea level rise, for planning purposes」,是规划洪水位。
- 实测 ✅(East Perth,Swan River 管理洪泛区):Floodplain Area 21 命中「Designated flood event floodplain」、DCA 54 命中、Extent 8 最近 21 m 未命中、Floodway 23 未命中 → 条件项;最近 Flood Level Point 的 `fldlvl_dfe` 2.28 m AHD,与地面层高差 0–2 m,Level 2 住面无虞,地下车库要问。

---

## 4. 山火

- 来源:Office of Bushfire Risk Management(DFES)"Bushfire Prone Areas",SLIP `Bush_Fire_Prone_Areas/MapServer`。已实测图层:**23 Bushfire Prone Areas (OBRM-026)**(含 `planningarea`、`transitionperiod`,是最新口径);17 Bush Fire Prone Areas (OBRM-001);21 designated on 13-12-2025 (OBRM-025);22 BFPA 2025 (OBRM-024);20 BFP Area Planning (OBRM-023)。目录:https://catalogue.data.wa.gov.au/dataset/bushfire-prone-areas-obrm-001

```bash
for L in 23 17 21 22 20; do echo "== $L"; q_wa Bush_Fire_Prone_Areas $L; done
q_wa Bush_Fire_Prone_Areas 23 1500   # 缓冲查,判断近邻
```
- 读法:命中则 `type=BPA`、`designation`(Bush Fire Prone Area…)、`designationdate`、`planningarea`(Bushfire Prone Area 1/2…)、`transitionperiod`。命中 = 开发需 BAL 评估(AS 3959),建筑与规划附加要求。
- 实测 ✅:点 **不在** BFPA;最近 BFPA 面 ≈448 m;图层 23 近邻两块:`lga=GOSNELLS, designationdate=1765584000000(2025-12-13)`。
- 判读:BFPA 每年按"指定日"更新(最新 2025-12-13),要用图层 23(最新)且报告标注日期;SPP 3.7 对 BFPA 内开发有强制要求,地块紧邻(<100 m)的要提示"周边植被可能影响 BAL"。

---

## 5. 滑坡 / 酸性硫酸盐土 / 污染场地 / 其它

| 项 | 来源与图层 | 命令 | 实测(22 Burnley St) |
|---|---|---|---|
| 酸性硫酸盐土(ASS) | DWER "Acid Sulfate Soil Risk Map, Swan Coastal Plain (DWER-055)",`Soil_Risk_Map/MapServer/3`(其它地区:4 Albany、5 Estuaries、6 Geraldton、7 Lower SW、8 Pilbara) | `q_wa Soil_Risk_Map 3` | ✅ 命中:`risk_class=2.0`、`risk_category=Moderate to low risk`、`natcode=2j (p4)`、`capture=Derived`、`create_date=1153267200000(2006-07-19)` |
| 污染场地 | DWER Contaminated Sites Database (DWER-059),`Environment/MapServer/5` | `q_wa Environment 5` 与 `q_wa Environment 5 300` | ✅ 点上 0,300 m 内 0。字段 `classification`(Contaminated – restricted use / Remediated for restricted use 等)、`report_url`。**该库只含已分类场地,"无记录≠无污染"** |
| 滑坡/地质风险 | 未发现 SLIP 公共滑坡图层(搜了 Geology_and_Soils_Map、Soil_Landscape 的图层名无 landslip)。珀斯滨海平原平坦,不是风险点。Soil_Landscape 有 Water Erosion Risk(DPIRD-013) | `未实测`(只列名) | ⚠️ 需要时查 DPIRD Soil Landscape 图层,Perth 住宅一般略过 |
| 噪音(道路/铁路) | DPLH SPP 5.4 Road and Rail Noise (Polygon, DPLH-057),`Property_and_Planning/MapServer/100` | `q_wa Property_and_Planning 100` | ✅ 0 命中(不在 SPP 5.4 噪音影响区) |
| Bush Forever / 保护 | 图层 89(SPP 2.8 Bush Forever Areas)、11(Swan Canning DCA) | `q_wa Property_and_Planning 89` | ✅ 0 命中 |
| 污水/排水区 | `Infrastructure_and_Utilities/MapServer/80`(Sewer Districts)、81(Declared Drainage Areas) | `q_wa Infrastructure_and_Utilities 80` | ✅ 已接污水区:`sd_number=SD068, sd_name=THORNLIE, wwtp=WOODMAN POINT`;排水区 0 命中 |

- ASS 判读:`risk_class` 1=高、2=中低(Swan Coastal Plain 的 DWER 分级编码)。**class 2 的含义:低-中风险,开挖/降水地下水需 ASS 评估触发条件,一般独立屋无影响**。分级定义以 DWER 元数据为准,**本表对 1–N 的细分描述未逐级核对原文**。
- **高程 / 等高线**:`Terrain/MapServer/0` 2 m contours(DPIRD-072),字段 `elevation_m`;250 m 缓冲几何查可用。珀斯滨海平原 2 m 线太稀(East Perth 250 m 内只采到 3 点),剖面只能写「平地,等高线间距 2 m」,不画坡度。地块环 + 等高线 + 路网(§8.3)三件凑齐可喂 `scripts/site_profile_svg.py`(独立屋);unit 不画。
- **学校**:`Education/MapServer/13`(DET-024,Semester 1 2026),字段 `schoolname / lowyear / highyear / sector`,只有校点,**无 local-intake area 多边形**;学区写「中介自述 + 最近公校点位距离 · 下一步:教育厅 Find a school 核」。
- **犯罪**:WA Police Crime Statistics 是 Power BI 页,HTML 无郊区数据 → 「需人用浏览器查」+ 入口 URL;**长期增长**:无官方成交层,只有 REIWA / Cotality 郊区中位(非官方,注明),30 年一律 none。

---

## 6. 官方估价

- ❌ **无免费逐地块 GRV/UV 接口**。
  - Landgate 的 GRV/UV "Valuation Extract" 是付费,单份 $10.20,认证副本 $22.00(出处:https://www.landgate.wa.gov.au/valuations/valuations-for-rates-and-taxes/valuation-extracts-reports/ ,2026-10-03 搜索摘要;费率每年 7 月随 CPI 调整)。按硬约束不使用。
  - 免费替代:① 客户自己的 City rates notice / 水费单(GRV、UV 都印在上面);② Landgate "GRV and UV statistics"(区/郊区级统计,非逐地块):https://www.landgate.wa.gov.au/land-and-property/property-ownership/property-sales-and-trends/grv-and-uv-statistics/ (未实测内容,仅确认页面存在);③ 估值只能当"州法定估值参考",**不是市场价**。
- 报告写法:"WA 官方逐地块估值需付费查询或看市政 rates notice,尽调用可比成交+AVM 代替"。

### 6b Strata 文件(unit;2026-10-27 读 Landgate 页)
- 免费源**一个都没有**:unit entitlement、楼层、总户数、levies、维修基金都不在任何公开图层。三条路:① 挂牌文案「Features and Rates」(WA 中介习惯写 Strata / Council / Water / Level / Total Strata Lots,本例全有:Level 2、115 lots、Strata $2,551.59 + $1,058.75/季、Council $2,888.85、Water $2,026.26)→ 报告标「**中介自述,待披露表核**」;② 卖方法定披露 **Precontractual disclosure statement**(Landgate「Resources for strata buyers」页原文;签约前必给);③ Landgate strata plan / survey-strata plan 副本 **$33.90**(「Survey plans and documents」页,2026-10-27 读取);签约后可付 $1 向 strata company 查档。WA 无公开 strata 公司登记。
- Landgate 子页 URL 变动频繁(本次猜 5 个错 4 个 404):只写根页 `https://www.landgate.wa.gov.au/strata-and-community-titles/` + 页内标题,从根页 href 列表找路径。
- **可比与中位(WA 无官方成交层)**:OnTheHouse 成交列表 `onthehouse.com.au/sold/wa/<suburb>-<pc>?page=N`(24 笔/页、12 个月窗口、含价格与房数、偶有面积,`curl` 无限速;`scripts/oth_sold_list.py`)+ 单元页(面积、strata lot 面积、文案含 levies、成交史)是唯一免费带价源(East Perth 12 个月 459 笔);Aussie 同楼单元页连抓 8 页触发 202 且几分钟内重试无效,**不要在脚本外并发抓**。
- 「两房 ≤ 区 house 中位一半」在公寓区落不了地(East Perth 12 个月 house 成交 17–22 笔,三家中位 $1.43M–$1.91M 相差 34%):house 样本 < 30–50 笔就写「本区独立屋样本不足,不作 house 替代判断」。

---

## 7. DA / 开发活动公开接口

- ❌ **没有免费、免登录的全州 DA 地图接口**。已实测:
  1. DPLH "Subdivision Applications (DPLH-087)" 和 "Strata Applications (DPLH-088)":目录页声明可下载,但 `https://data-downloads.slip.wa.gov.au/DPLH-087/GeoJSON` → 302 到 SLIP SSO 登录页;`services.slip.wa.gov.au/arcgis/rest/.../DPLH_Restricted_Government_Services/MapServer/13` → **401 Unauthorized**。两者都要 SLIP 账号(免费注册但需登录,代理不创建账号)。
  2. SLIP 公共服务里没有 DA 登记图层(已按名称扫描 Property_and_Planning / People_and_Society 等 17 个服务)。
  3. 小范围能用的公开边角数据:图层 49 "Region Scheme - Applications (DPLH-021)"(MRS 修正申请,不是住宅 DA),`Property_and_Planning/MapServer/49`,**未命中/未专项实测**。
- ⚠️ 需浏览器人工:① 市政 DA 登记册(City of Gosnells 规划页,curl 直接 403,需浏览器:https://www.gosnells.wa.gov.au/Building-Development-and-Business/Planning ); ② DPLH Planning Online 提交入口 https://planningonline.dplh.wa.gov.au/ (200 可达,公开登记册功能**未实测**);③ DAP 清单在 DPLH 站点。
- 备选(非官方,仅线索):AreaSearch 等第三方,不计入官方源。

---

## 8. 道路车流量 / 铁路 / 机场

### 8.1 Main Roads WA Traffic Digest(官方开放数据,CC BY 4.0)
- 来源:`https://gisservices.mainroads.wa.gov.au/arcgis/rest/services/OpenData/RoadAssets_DataPortal/MapServer/27`(Traffic Digest);数据集目录 https://catalogue.data.wa.gov.au/dataset/mrwa-traffic-digest ;元数据:数据更新 2025-06-05。同服务另有 17 Road Network、15 Rail Crossing、9 Legal Speed Zones(未实测)。

```bash
curl -s -G "https://gisservices.mainroads.wa.gov.au/arcgis/rest/services/OpenData/RoadAssets_DataPortal/MapServer/27/query" \
 --data-urlencode "geometry={lon},{lat}" --data-urlencode "geometryType=esriGeometryPoint" --data-urlencode "inSR=4326" \
 --data-urlencode "spatialRel=esriSpatialRelIntersects" --data-urlencode "distance=2000" --data-urlencode "units=esriSRUnit_Meter" \
 --data-urlencode "outFields=ROAD_NAME,LOCATION_DESC,TRAFFIC_YEAR,MON_FRI,MON_SUN,PCT_HEAVY_MON_FRI" \
 --data-urlencode "returnGeometry=true" --data-urlencode "outSR=4326" --data-urlencode "f=json"
```
- 读法:`MON_FRI`=都会区"典型工作日"双向车辆数,`PCT_HEAVY_*`=重车比例,`TRAFFIC_YEAR`=统计年。
- 实测 ✅:500 m / 1000 m 内 0 个点(Burnley St 是本地街,Main Roads 不计数);2 km 内 11 个。最近的几个:Yale Rd(西 McMahon St,2022/23,MON_FRI 10,956,重车 6.3%);Burslem Dr(Albany Hwy 以西,2023/24,13,839);Albany Hwy(Burslem Dr 以南,2023/24,30,168);Kenwick Link(Osmond St 以北,2023/24,28,212);Spencer Rd(Wilfred Rd 以南,**`TRAFFIC_YEAR=2026/27`**,33,973)。
- 判读:只覆盖 Main Roads 计数的干道,本地街没有数据,要用邻近干道 + 街道等级判断。⚠️ `TRAFFIC_YEAR=2026/27` 属数据异常或预测值,**未核实原因**,使用时以数据集元数据为准。

### 8.2 铁路
- SLIP Transport 服务没有铁路线几何图层。可用代替:`Transport/MapServer/14`(PTA Stops,筛 `stoptype='Rail'`)。

```bash
curl -s -G "$SLIP/Transport/MapServer/14/query" --data-urlencode "where=stoptype='Rail'" \
 --data-urlencode "geometry={lon},{lat}" --data-urlencode "geometryType=esriGeometryPoint" --data-urlencode "inSR=4326" \
 --data-urlencode "spatialRel=esriSpatialRelIntersects" --data-urlencode "distance=4000" --data-urlencode "units=esriSRUnit_Meter" \
 --data-urlencode "outFields=stopname,stoptype" --data-urlencode "returnGeometry=true" --data-urlencode "outSR=4326" --data-urlencode "f=json"
```
- 实测 ✅:最近火车站 Thornlie Stn ≈1,606 m,Maddington Stn ≈1,796 m,Kenwick Stn ≈2,263 m。图层 33 "PTA Rail Distance Measures (PTA-005)" 的里程点最近 2,295 m(哪条线未标注,**未核实**);所以"离铁轨多远"只能用车站做近似,噪音走 SPP 5.4(见第 5 节,0 命中)。
- 公交路线 `Transport/MapServer/15` 只含公交线(实测均为公交 routename)。

### 8.3 路网几何(画地块图 / 判临街边用)
- `Transport/MapServer/16`(Roads Simplified)对几何查返回 400;用 **18(Main Roads)/ 19(Minor Roads)**,字段 `road_name`,120 m 缓冲几何查。步行距离用 OSRM `routed-foot`(写法在 `state-method.md`)。

### 8.3 机场 / ANEF
- SLIP:SPP 5.1 Perth Airport 周边(`Property_and_Planning/MapServer/77`)、SPP 5.3 Jandakot Airport 周边(78)。实测 ✅ 本点 **均 0 命中**。
- ⚠️ ANEF 噪音等值线本身没有免费 REST 图层;Jandakot/Perth Airport 官方 ANEF 以机场总体规划 PDF 为准(人工查机场官网 master plan)。SPP 5.1/5.3 范围外通常意味着不在 ANEF 20 以上区。

---

## 9. 政策红利(只引官方原文+日期)

1. **WA R-Codes Vol 1 现行版 = "Residential Design Codes Volume 1 – April 2026"**(Volume 2 = April 2024)。出处:https://www.wa.gov.au/government/document-collections/residential-design-codes (2026-10-03 读取)。同页原文:granny flats can now be constructed "on all residential zoned land, including grouped and multiple dwellings and strata lots";Part C 特殊过渡期 **2026-04-10 到期**(R50+ 结构规划区单户开发须满足 Part C)。
2. **Granny flat(ancillary dwelling)豁免**:WA 政府声明(Planning, 2024-04-16):"R-Code compliant granny flats can now be built on residential lots of any size without planning approval if they meet relevant local area setback requirements and do not exceed 70m2";**生效 2024-04-10**。出处:https://www.planning.wa.gov.au/news-and-media-statements/revised-r-codes-now-in-effect (同一声明另见 https://www.wa.gov.au/government/announcements/revised-r-codes-now-effect )。部长声明(2024-01-29)原话:"A minimum lot size will no longer apply"、"Planning approval not required for compliant granny flats up to 70sqm",https://www.wa.gov.au/government/media-statements/Cook-Labor-Government/More-granny-flat-exemptions-give-another-boost-for-housing-choice-20240129 。City of Gosnells 对应页:非农村分区、须满足退线、70 m² 上限(https://www.gosnells.wa.gov.au/Building-Development-and-Business/Planning/Planning-Information/Ancillary-Dwellings ,读取内容为摘要)。
3. **R40 本身**:不同 R 码允许的最小/平均地块面积在 R-Codes Vol 1 表 2.1(现版本),本说明**未核对具体面积数字**,按 Vol 1 April 2026 原文+Gosnells LPS 24 条款核。LPS 24 刊宪日 2025-09-30(来自 DPLH-071 图层属性)。
4. 结论用法:22 Burnley St(R40、约 804 m²、Plan 8818 独立地块)→ 加盖 ≤70 m² granny flat 路径,在退线合规时**无需规划批准**(只需建筑许可);分块/双拼走 Vol 1 R40 条款与 WAPC 分块审批(**须人工核对**)。BFPA 不涉及。
5. ⚠️ 其它 WA 红利(Medium-density Housing Code / Vol 3 等)只在 R-Codes 合集页看到名字,未逐条核,**不写入判读**。

---

## 10. 测试地址实测结果汇总表(22 Burnley St, Thornlie WA 6108)

| # | 检查项 | 状态 | 关键返回 |
|---|---|---|---|
| 1a | 地址→坐标→地块多边形 | ✅ | land_id 1505172;中心 115.96552,-32.05638;面积自算约 804 m² |
| 1b | Plan/Lot、strata | ⚠️ 部分 | Plan P8818(Deposited Plan,非 SP 前缀 = 非 strata);Lot 号拿不到(需付费查册) |
| 2a | Zone | ✅ | Residential;City of Gosnells(LPS 24,刊宪 2025-09-30) |
| 2b | R-Codes | ✅ | R40 |
| 2c | MRS | ✅ | Urban |
| 2d | 遗产 | ✅ | 州登记/Heritage List/Local Heritage Survey/Heritage Areas 点上均 0;300 m 内 3 处 LHS 邻近 |
| 3 | 洪水(DWER FPM) | ✅ 不在 | 最近洪泛范围约 565 m,DCA 约 273 m(Canning River) |
| 4 | 山火 BFPA | ✅ 不在 | 最近 BFPA 448 m;最新指定日 2025-12-13 |
| 5a | 酸性硫酸盐土 | ✅ 命中 | risk_class 2 "Moderate to low risk" |
| 5b | 污染场地 | ✅ 无记录 | 点上及 300 m 内 0 |
| 5c | 滑坡 | ⚠️ 无公共图层 | 珀斯平坦,略 |
| 5d | SPP 5.4 噪音 | ✅ 不在 | 0 |
| 6 | 官方估价 GRV/UV | ❌ 无免费逐地块源 | Landgate 估值摘录付费 $10.20;用 rates notice |
| 7 | DA/开发活动 | ❌/⚠️ | DPLH-087/088 需 SLIP 登录(401/302);市政页需浏览器 |
| 8a | 车流量 | ✅ 附近干道 | Albany Hwy 30,168(2023/24)、Yale Rd 10,956(2022/23);Burnley St 本身无计数 |
| 8b | 铁路 | ✅ 近似 | Thornlie Stn 1,606 m;无线路几何 |
| 8c | 机场 | ✅ 不在 | SPP 5.1 / 5.3 范围外;ANEF 本体需人工 |
| 9 | 政策红利 | ✅ 官方原文 | R-Codes Vol 1 April 2026;granny flat ≤70 m² 免规划批准,2024-04-10 生效 |

## 10b. Unit 实测结果汇总表(18/90 Terrace Road, East Perth WA 6004,2026-10-27;`scripts/wa_layers.py --config templates/layers-WA.json` 跑的 33 层)

| # | 检查项 | 状态 | 关键返回 |
|---|---|---|---|
| 1 | 地址 → 母地块 → strata | ✅ | Cadastre Address 只有母地址(无单元记录);Plan Extent 3 plan 叠放,取 SP 58159;Cadastre No Attributes 116 多边形 = 115 户 + 共用 |
| 2 | Zone / R-Code / MRS | ✅ | City of Perth(City Planning Scheme No. 2);MRS Urban |
| 2d | 遗产 | ✅ 命中 | State Register Place 14911(前 ABC 演播室改建)、Heritage List、Local Heritage Survey 均命中;inHerit 正文 JS 渲染,curl 只拿到标题,写「州遗产登记地 + 链接」 |
| 3 | 洪水(DWER) | ⚠️ 条件项 | Floodplain Area 21 命中、DCA 54 命中、Extent 8 最近 21 m、Floodway 23 未命中;`fldlvl_dfe` 2.28 m AHD |
| 4 | 山火 BFPA | ✅ 不在 | 0 |
| 5a | 酸性硫酸盐土 / 污染场地 / Bush Forever | ✅ 不在 | 0 / 0 / 0 |
| 5d | SPP 5.4 噪音走廊 | ✅ 命中 | Property_and_Planning 100 命中(Riverside Dr / Terrace Rd) |
| 5e | 排水区 | ✅ 命中 | Declared Drainage Area 命中 |
| 6 | 估价 / strata 文件 | ❌ 无免费源 | 中介文案:Level 2、115 lots、strata 约 $14,441/年、council $2,888.85、water $2,026.26 → 标「中介自述」;披露表与 strata plan 副本 $33.90 |
| 7 | 可比 | ✅ OnTheHouse | 12 个月 459 笔;同楼 3 房三笔 $1.38M–$1.50M |
| 8 | 机场 | ✅ 不在 | SPP 5.1 / 5.3 范围外 |
| 9 | 学校 | ⚠️ 只有校点 | Education/13 最近公校点位;无学区多边形 |
| 10 | 照片 | ⚠️ 1 张 | Aussie 页 32 张图由 JS 加载,HTML 只有 1 张 og:image;建材「未判」 |
| 时间 | 墙钟 26 分钟 / 等权限 0 / 模型 23(+ 子代理 12)/ 需人 0 | | |

## 11. 未解决 / 存疑清单

1. WA **Lot 号**与**法定面积**:免费源无,需产权查册(付费)或客户提供;报告须写"自算面积,以产权为准"。
2. **逐地块 GRV/UV**:无免费接口。
3. **DA 登记**:DPLH-087/088 要 SLIP 登录(免费注册但代理不能代建账号);Gosnells 规划页 curl 403,需浏览器。DAP 清单、Planning Online 公开登记册功能**未实测**。
4. **铁路线几何**缺失;"PTA Rail Distance Measures" 对应哪条线未核实。
5. **ANEF 等值线**无免费 REST,需机场 master plan PDF。
6. Traffic Digest 出现 `TRAFFIC_YEAR=2026/27`(Spencer Rd 站点),原因未核实;数据整体 2025-06-05 更新。
7. R40 的具体地块面积/退线/容积率数值**未核对**(要读 R-Codes Vol 1 April 2026 原文表格)。
8. 图层号随 SLIP 版本变化的风险(图层名带 DPLH/DWER/OBRM 编号是稳定标识);BFPA 的 5 个图层中 17/20/21/22 与 23 的差异(历史版本 vs 当前)是**按名称推断**,只确认了 23 含 `planningarea`/`transitionperiod` 字段。
9. ASS risk_class 数值与描述的完整对照表未逐级核对。
10. 滑坡/岩土风险无公共图层(Perth 影响小,山坡区如 Perth Hills 需人工)。
