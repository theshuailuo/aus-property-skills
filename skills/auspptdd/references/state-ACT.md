# ACT(澳大利亚首都领地)辖区适配说明 · auspptdd

- 实测日期:2026-10-03(本机 curl / Python urllib / Browser pane)
- **测试地址**:30 Diamantina Crescent, Kaleen ACT 2617(Belconnen district;Section 110 Block 23 Kaleen)
- **测试坐标(WGS84,来自 ACT 官方地址点,图层字段 LONG/LAT)**:lon = 149.10096628,lat = -35.22851825(几何返回值 149.10096071, -35.22853111,同点)
- 官方数据平台:**ACTmapi / ACT Government 的 ArcGIS Online 组织**(已核实组织名:`Australian Capital Territory Government`,urlKey `ACTGOV`)。要素服务根目录:
  `https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services`(匿名可读,约 387 个服务)。另有 **data.act.gov.au**(Socrata;ACTGOV BLOCK 数据集 id `h78d-hg25`,ACT Addressing `rwvc-ci8y` 等,多数是 ArcGIS 地图的外链)。
- 全局注意:ACT 图层原生坐标系是 GDA2020 / MGA55(wkid 7855),`inSR=4326` 点查正常工作。命令里 `{lon} {lat}` = WGS84 十进制度。所有 FeatureServer 都有 `maxRecordCount`(地址层 1000)。
- ACT 特殊性:**ACT 全部土地是 Crown 租赁(leasehold)**,无 freehold;block 的"所有权"=对 Territory 的长期租约(通常 99 年,购买时转让的是租约)。block 层的 `BLOCK_LEASED_AREA` 在测试块为 null,**租约期限/用途条款(purpose clause)/租金不在免费图层里**,见 §1d。

---

## 1. 地址 → 坐标 → 地块(block/section/district、面积、边界、unit title、leasehold)

### 1a 地址 → 坐标
- 来源:`ACTGOV_ADDRESSES/FeatureServer/0`(ACT 官方 assigned addresses 点)
  出处:https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_ADDRESSES/FeatureServer/0
- 字段(实测):`DISTRICT`、`DIVISION`(**= 郊区名 suburb**)、`SECTION`、`BLOCK`、`BUILDING_NAME`、`DOOR_NO`、`UNIT_TITLE`、`UNIT_CLASS`、`UNITPLAN_NO`、`ADDRESS_ID`、`STREET_NUMBER`、`STREET_NAME`、`STREET_TYPE`、`LONG`、`LAT`(字符串)、`VOLUME_FOLIO`、`ASSIGNED`、`SUBADDTYPE`、`BLOCK_KEY`。(**没有 SUBURB/ADDRESS 字段**,用 DIVISION 当郊区。)
- 命令:
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_ADDRESSES/FeatureServer/0/query" \
  --data-urlencode "where=STREET_NUMBER='{N}' AND STREET_NAME='{STREET}' AND STREET_TYPE='{TYPE}' AND DIVISION='{SUBURB}'" \
  -d "outFields=ADDRESS_ID,SECTION,BLOCK,BLOCK_KEY,VOLUME_FOLIO,UNIT_TITLE,UNITPLAN_NO&returnGeometry=true&outSR=4326&f=json"
```
- 实测状态:✅ `30 DIAMANTINA CRESCENT KALEEN` → ADDRESS_ID 342018,SECTION 110,BLOCK 23,BLOCK_KEY 55531100023,VOLUME_FOLIO "630:14",UNIT_TITLE null;geometry x=149.10096071 y=-35.22853111。
- 注意:全部字段大写;`STREET_TYPE` 用全称(CRESCENT/STREET),不是缩写;单元址 `STREET_NUMBER` 会带后缀(如 `24A`),`DOOR_NO='1'`、`UNIT_TITLE='1'`、`UNITPLAN_NO='1562'`。

### 1b 坐标 → block(地块)
- 来源:`ACTGOV_BLOCKS/FeatureServer/0`(ACTGOV BLOCK;"最小可单独持有租约的地块";同时是 data.act.gov.au `h78d-hg25`)
- 命令:
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_BLOCKS/FeatureServer/0/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
  取边界:`returnGeometry=true&outSR=4326`。按 block key 查:`-d "where=BLOCK_KEY={BLOCK_KEY}"`。
- 返回字段怎么读:
  - `SECTION_NUMBER` + `BLOCK_NUMBER` + `DIVISION_NAME`/`DISTRICT_NAME` = ACT 的地块标识(**Division/Section/Block**,不是 lot/DP);
  - `BLOCK_DERIVED_AREA`(字符串,m²;GIS 推导面积)、`BLOCK_LEASED_AREA`(租约面积,常为 null);
  - `VOLUME_FOLIO`(Certificate of Title 卷/页;"…  -  other volume and folios found with this lease" 表示该 block 下多本);
  - `PLAN_NUMBERS`:含 AP/DP/POL/X…;**含 `UP{n}`(Units Plan)= 该 block 上有 unit title(strata 等价物)**;
  - `LAND_USE_POLICY_ZONES`(如 `RZ1: SUBURBAN`)、`OVERLAY_PROVISION_ZONES`、`NEW_TERRITORY_PLAN`(= "Territory Plan Land Use Policies: RZ1: SUBURBAN",**与 Territory Plan 2023 命名一致**);
  - `CURRENT_LIFECYCLE_STAGE`(REGISTERED=已登记)、`TYPE`(URBAN)、`SENSITIVE_FLAG`(敏感)。
- 实测状态:✅ 测试地址 → BLOCK_KEY 55531100023,**BLOCK_DERIVED_AREA 928**(Shape__Area 928.86 m²),VOLUME_FOLIO 630:14,PLAN_NUMBERS "AP29, POL2367, X10584, DP4207",ADDRESSES "30 DIAMANTINA CRESCENT*",LAND_USE_POLICY_ZONES **"RZ1: SUBURBAN"**,OVERLAY_PROVISION_ZONES null,CURRENT_LIFECYCLE_STAGE REGISTERED,TYPE URBAN。
- 判读注意:`ADDRESSES` 里带 `*` 的是主地址;一个 block 上多个地址(双拼/unit)会逗号分隔。

### 1c unit title(strata 等价物)
- 来源:`ACTGOV_UNIT/FeatureServer/0`(单元地块;字段 `UNIT_NUMBER`、`UNIT_PLAN_NO`、`UNIT_ADDRESS`、`BLOCK_KEY`、`UNIT_CLASS`、`CURRENT_LIFECYCLE_STAGE`)
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_UNIT/FeatureServer/0/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 判断规则(实测验证):
  1. 地址层 `UNIT_TITLE IS NOT NULL` 或 `UNITPLAN_NO` 有值 → 单元地址;
  2. `ACTGOV_UNIT` 点命中 → 单元;测试地址 0 条(= 独立屋 block)。
  3. block 层 `PLAN_NUMBERS` 含 `UP{n}`。
- 实测状态:✅ 对照 `24A Burnett Street Kaleen`(UNIT_TITLE 1,UNITPLAN_NO 1562):ACTGOV_UNIT 返回 UNIT_NUMBER "1",UNIT_PLAN_NO "1562",UNIT_ADDRESS "1/24A BURNETT STREET, KALEEN";其所在 block(BLOCK_KEY 55530010012,948 m²)PLAN_NUMBERS 含 "UP1562"、VOLUME_FOLIO "1507:20 - other volume and folios found with this lease"、ADDRESSES "24 BURNETT STREET*, 24A BURNETT STREET*"。
- 注意:ACT unit 的 **UV/租约份额**在 units plan(Access Canberra / ACT Land Titles Register),不是免费图层。

### 1d Crown lease(leasehold)要点
- 免费图层可得:block 面积、租约关联卷册、zone、DA 历史。
- **免费图层得不到**:租约起讫(99 年起算日)、**purpose clause**(用途条款,决定能否多户)、租金、租约变更历史(Lease Variation Charge)。这些在 Crown lease 文件/ACT Land Titles Register(Access Canberra,通常收费)。**⚠️ 未实测任何免费入口**。
- 估价/增值的关键:`unimproved value` 反映 "the most valuable use of the property permitted by its Crown Lease purpose clause"(ACT Revenue Office 页原文,见 §6);改租约(增加 dwelling 数)要缴 **Lease Variation Charge(LVC)**,见 §9。
- 人工入口:https://www.planning.act.gov.au (Crown leases 说明页,路径 `/community/buy/leasing-and-titles/crown-leases/...`,由 revenue.act.gov.au LVC 页引用,**未实测打开**)。

---

## 2. 规划分区 zone + overlays(含 heritage)

### 2a Zone(Territory Plan)
- 首选(最直接):§1b 的 `LAND_USE_POLICY_ZONES` / `NEW_TERRITORY_PLAN`(block 层自带,已是 Territory Plan 2023 的 RZ1–RZ5/CZ/… 命名)。
- 区域面图层:`ACTGOV_TP_LAND_USE_ZONE/FeatureServer/1`「Territory Plan Land Use Zones」
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_TP_LAND_USE_ZONE/FeatureServer/1/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 实测状态:✅ 测试地址 → `LAND_USE_ZONE_CODE_ID RZ1`,`LAND_USE_POLICY_DESC SUBURBAN`,`CURRENT_LIFECYCLE_STAGE GAZETTED`,`VARIATION_NUMBER_CREATED_BY "TP 2008"`,`GAZETTAL_NUMBER NI2008-27`,`GAZETTAL_DATE 1206921600000`(= 2008-03-31),`DIVISION_NAME KALEEN`。全域 RZ1 多边形共 978 个。
- **判读注意(重要)**:这个面图层的 `GAZETTAL_*`/`VARIATION_*` 元数据是 **2008 年旧 Territory Plan 的变更号**,**不能当作 Territory Plan 2023 的生效日期**;用它只取「zone 代码」,zone 在 Territory Plan 2023(2023-11-27 新规划体系启动,据 revenue.act.gov.au RZ1 页与搜索摘要)下的条文要求要去 Territory Plan 2023 的 Zone 条文(planning.act.gov.au)。

### 2b Overlays
- 图层:`ACTGOV_TP_OVERLAY_ZONE_POLY/FeatureServer/0`(字段 `ZONE_OVERLAY_CODE_ID`、`OVERLAY_PROVISION_DESC`、`VARIATION_NUMBER_CREATED_BY`、`GAZETTAL_DATE`)与 `ACTGOV_TP_OVERLAY_ZONE_LINE`。
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_TP_OVERLAY_ZONE_POLY/FeatureServer/0/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 实测状态:✅ 测试地址 0 条。已见 `ZONE_OVERLAY_CODE_ID` 值:A(National land subject to master plan)、FUA(Future Urban Areas)、KFa–KFe(Kingston Foreshore)、Pa/Pb/Pc/Pd(Wilderness/National Park/Nature Reserve/Special Purpose Reserve)…(distinct 前 60 条,全表更多)。
- **判读注意**:该图层看起来是**旧体系的 overlay(precinct/Future Urban Area/reserve 类)**;Territory Plan 2023 的新体系 overlay(如 Bushfire、heritage、flood、tree、biodiversity 等)**不全在此图层**。2023 新体系 overlay 是否有独立要素服务:**未找到/未实测**,需要在 ACTmapi 浏览器上用「Territory Plan」视图人工确认(https://actmapi-actgov.opendata.arcgis.com 为 ACTmapi 开放数据门户,**未实测打开**)。

### 2c Heritage
- 来源:`ACTGOV_Heritage_Register/FeatureServer/1`(ACT Heritage Register;受 Heritage Act 2004;敏感点已去标识)
  出处:https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_Heritage_Register/FeatureServer/1
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_Heritage_Register/FeatureServer/1/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=NAME,HRcategory,HeritageID,HRstatus,BLOCK_NUMBER,SECTION_NUMBER,DIVISION_NAME&returnGeometry=false&f=json"
```
- 字段:`NAME`、`HRcategory`(Historic place or object / …)、`HRstatus`(如 "3 - Registered Places or Objects")、`HeritageID`、`DataRestrictions`。
- 实测状态:✅ 测试地址 0 条;阳性对照(National Rose Gardens 一带 envelope):`NAME "National Rose Gardens"`,`HRcategory "Historic place or object"`,`HRstatus "3 - Registered Places or Objects"`,`HeritageID 400`,Section 34 Block 6 Parkes。
- 判读注意:登记册只含「已登记」;**Aboriginal 敏感地点被去标识/不在公开图层**(服务描述原文:"All restricted data has been de-identified, with sensitive sites ...");登记 ≠ 无其它保护(Heritage precinct overlay、Territory Plan 2023 的 heritage 要求另查)。

---

## 3. 洪水(含「storm surge」——ACT 内陆,不适用)

- 来源:`ACTGOV_FLOOD_EXTENT/FeatureServer/0`「1 in 100 year Flood model extent (1% AEP)」(只有 OBJECTID/面积字段,多边形仅表示范围)
  另有 `Flood_Boundary` 服务(未实测)。
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_FLOOD_EXTENT/FeatureServer/0/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 实测状态:✅ 测试地址 0 条;阳性对照(envelope 149.0–149.3, -35.5– -35.1)命中 1 个大多边形(OBJECTID 1,面积 ≈ 2.47e7 m²)。
- 判读注意:
  1. 返回的只有「在不在 1% AEP 模型范围内」,**没有水深/流速/hazard 分级**;
  2. **未建模的支流/街道漫流不会出现**,0 条≠无洪水风险(ACT 有 flood-prone 概念要看 Territory Plan 2023 与 EPSDD flood 说明,未实测);
  3. ACT 没有 storm surge(内陆领地)。

---

## 4. 山火(Bushfire Prone Area)

- 来源:`Bushfire_Prone_Area_Overview_2026/FeatureServer/0`(服务描述:"The ACT's Bushfire Prone Area 2026";另有 `Bushfire_Prone_Area_Details_2026`,未实测字段)
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/Bushfire_Prone_Area_Overview_2026/FeatureServer/0/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 实测状态:✅ 测试地址 0 条(未在 BPA 内);阳性对照 (149.0560, -35.4000,Tuggeranong 南)命中 1 个大多边形(面积 ≈ 2.11e9 m²)。
- 判读注意:图层只有面积字段,**仅「在/不在 BPA」二元**;BAL 等级与 Bushfire Abatement Zone 需另查 `Bushfire_Prone_Area_Details_2026`/EPSDD 说明(未实测)。2003 火灾影响范围另有数据集(data.act.gov.au `8gwk-tw75`,仅供历史对照)。

---

## 5. 滑坡 / 酸性硫酸盐土 / 海岸 / 其它

- **滑坡**:ACT 无公开的 landslide hazard band 服务(服务目录名称关键词扫描 landslip/landslide=0)。**❌ 无免费源**(坡度风险→看地形/LiDAR,不在本次范围)。
- **酸性硫酸盐土**:ACT 无海岸 ASS 概念;**❌ 不适用**。
- **海岸侵蚀/淹没**:**不适用**(内陆)。
- **土壤盐渍(ACT 特有、相关)**:`ACTGOV_HGL_Hydrogeological_Landscapes/FeatureServer/0`
  实测 ✅ 测试地址命中 `HGL "Bruce"`,`HGL_NO 4`,`SALT_LAND "Moderate"`,`HAZ_IMPACT "Significant"`,`HAZ_LIKELI "Moderate"`,`HAZ_OVRALL "Moderate"`,`DATA_RELIB "Moderate"`。含义:盐害(salinity)风险提示,**用于结构/景观判断,不是 ACT 估价口径**。
- **土壤景观**:`ACTGOV_Soil_Landscapes/FeatureServer/0` 测试点返回 `masterName "Winnunga"`,描述为「NE ACT 的 Ordovician metasediments 缓坡」——与 Kaleen 位置**不符合预期**,疑似粗尺度/匹配不准,**存疑,不入报告**。
- **环境噪声分区**:`Noise_Zones/FeatureServer/0–7`(Zone A–G、AIRPORT;依 Environmental Protection Regulation 2005)。实测 ✅ 测试地址落在 Zone G("All other land, including- residential land (RZ1-5), hills, ridges and buffers";白天 45 dB(A)、夜间 35 dB(A))。**这是环境噪声规则分区,不是 ANEF**。
- 污染地:ACT 污染地登记册(Contaminated sites)**未找到免费空间服务,未实测**。

---

## 6. 官方估价(Unimproved Value,UV)

- 官方免费公开查询:✅ **存在**——ACT Revenue Office 指向的 **Unimproved Value register(Access Canberra)**
  入口 URL:https://services.accesscanberra.act.gov.au/s/public-registers/unimproved-land-values?registerid=unimproved-values
  - 实测:Browser pane 打开成功,页面文字原文(摘):"The Commissioner for ACT Revenue redetermined the 2026 unimproved values on 23 June 2026."(= **2026 年 UV 已于 2026-06-23 重新厘定**);表单为「Select a Suburb → …」(Salesforce LWC,Shadow DOM,找不到可脚本化的 input);免责声明:"This UV look-up is intended for use by you as a guide only ... does not replace a notice of a determination of the unimproved value ..."
  - **本次未提交表单取得测试地址 UV**;状态判定:⚠️ **免费,但需浏览器人工(suburb → section → block)**。`data.act.gov.au` Socrata 目录搜索 unimproved/valuation = 0 个数据集,**没有开放数据 API**。
- 官方口径(revenue.act.gov.au/rates-and-property-charges/land-valuations 页,2026-10-03 取得):
  - UV 定义上不含 lessee improvements(建筑、景观、铺路、围栏);原文关键句:"The unimproved value reflects the most valuable use of the property permitted by its Crown Lease purpose clause. The unimproved value is often different to the market value of the property."
  - "The ACT Revenue Office updates the unimproved value of properties every year. ACT Government property charges are based on the average unimproved value (AUV) of the property over 5 years."
  - Valuation notice 按 1 月 1 日基准(页面原文:"The notice will show the property's unimproved value as of 1 January that year");**个别 unit owner 不收到估值通知,通知发给 owners corporation**。
  - 自助服务「Your property valuation」需登录(页面原文:"Sign in to Your property valuation";该服务可 "See your property's unimproved value (excluding units)")——面向业主,不是公开逐地块查询;公开逐地块查询是上面的 UV register。
- 判读注意:**UV 是地价口径,不是市价/不含房屋**;不要拿 UV 当 CMA。样板:ACT 买卖价格看 RP Data/REA(付费)或 ACT 土地交易登记。

---

## 7. DA / 开发活动公开接口

- ✅ **有官方公开接口**(ACT 是 3 个辖区里最好的)
  - Active:`ACTGOV_ACTIVE_DEVELOPMENT_APPLICATIONS/FeatureServer/0`(共 1,408 条)
  - Completed:`ACTGOV_COMPLETED_DEVELOPMENT_APPLICATIONS/FeatureServer/0`(共 157,715 条)
  - 说明原文:"Active Development Applications for design and siting and/or variation of leases in the ACT"
  - 另有 `ACTGOV_DAFINDER_PREDA_LIST_VIEW`(pre-DA,未实测)
  - 字段(Active):`DA_NUMBER`、`ACTIVITY`、`BLOCK_KEY`、`DISTRICT`、`DIVISION`、`SECTION`、`BLOCK`、`LODGEMENT_DATE`、`APPLICATION_TYPE`、`SUBCLASS`(如 NEW DEVELOPMENT / DESIGN AND SITING / OTHER SERVICES);Completed 另有 `DECISION`、`DECISION_DATE`、`ELAPSED`(天)、`STATUS`、`ACTUAL_FINISH_DATE`。
```bash
# 本块的历史 DA
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_COMPLETED_DEVELOPMENT_APPLICATIONS/FeatureServer/0/query" \
  -d "where=BLOCK_KEY={BLOCK_KEY}&outFields=*&returnGeometry=false&f=json"
# 周边在审 DA(envelope 约 ±300 m)
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_ACTIVE_DEVELOPMENT_APPLICATIONS/FeatureServer/0/query" \
  -d "geometry={lon_w},{lat_s},{lon_e},{lat_n}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 实测状态:✅
  - 本块(BLOCK_KEY 55531100023)历史 DA:**DA 200913874**,LODGEMENT_DATE 1234224000000(= 2009-02-10),DECISION_DATE 1242172800000(= 2009-05-13),DECISION "Approval Conditional",ELAPSED 62,SUBCLASS = DESIGN AND SITING / SINGLE DWELLING / OUTBUILDINGS(同一 DA 号三条子类行)。
  - 周边约 1.1 km × 0.8 km envelope(149.095–149.107, -35.232– -35.225)Active DA:返回多条 **DA 202443004**(Section 141 Block 8 Kaleen,LODGEMENT_DATE 1731456000000 = **2024-11-13**,SUBCLASS = NEW DEVELOPMENT / DESIGN AND SITING / OTHER SERVICES,APPLICATION_TYPE SUBC)。
- 判读注意:**一个 DA 号对应多行(每个 SUBCLASS 一行,甚至重复几何)**,去重要用 `DA_NUMBER`;`DECISION` 要对 Completed 层看;没有 DA 文字描述/申请人/金额,详情要去 DA Finder(planning.act.gov.au,未实测)。

---

## 8. 道路车流量、铁路线、机场 ANEF

### 8a 车流量
- ❌ **未找到免费逐路段 AADT 开放数据**。已试三条:
  1. ArcGIS 组织服务名扫描:只有 `Road_Network_including_speedzones`、`ACTGOV_Road_Network_2025_Speed_Zones_view`(限速,无流量)、信号灯/交通岛资产;
  2. data.act.gov.au 目录搜 "traffic":有 `jn4p-azhb` Traffic Links Stats、`mgzi-6f8j` Traffic Route Stats(**实测内容=2020-05 起的行程时间/拥堵统计,含路段名+几何,字段 TT/Delay/Speed,不是 AADT**)、`eerp-hh34` Parks and Conservation Traffic Counters(公园入口计数)、`cjkg-rvmu` realtime traffic;
  3. 搜索 hub 无 ACT AADT。
- 用途:Traffic Links Stats 可粗看主干路拥堵趋势;**不得当 AADT**。
- 人工:Transport Canberra and City Services(TCCS)交通计数报告页(**未实测**)。

### 8b 铁路(含轻轨)
- `ACTGOV_RAILWAY/FeatureServer/0`(centreline,字段 `CURRENT_LIFECYCLE_STAGE`、`LAST_UPDATE_DATE`);另有 `Transport_Canberra_Light_Rail_Route_view`、`..._Station_view`、`LightRailStops2`(未实测字段)。
```bash
curl -s -G "https://services1.arcgis.com/E5n4f1VY84i0xSjy/arcgis/rest/services/ACTGOV_RAILWAY/FeatureServer/0/query" \
  -d "geometry={lon_w},{lat_s},{lon_e},{lat_n}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 实测:✅ 阳性对照(Canberra City 一带 envelope)返回 OPERATIONAL 段;测试地址 Kaleen 周边不在铁路/轻轨上(未专门做测试地址 envelope,**仅位置常识判断**)。距离需用 `geometryType=esriGeometryPoint` + `distance=500&units=esriSRUnit_Meter`。

### 8c 机场 / ANEF
- ⚠️ **ANEF 等值线本身不在 ACT 免费空间服务里**。ACT 提供:
  - `Noise_Zones`(环境噪声分区,含 layer 7 "AIRPORT",**实测测试地址不在 AIRPORT 区**);
  - `ACTGOV_TRANSPORT_AIRPORT_POLY` / `..._LINE`(机场设施面/线,不是噪声);
  - 官方 ANEF 来自 **Canberra Airport Master Plan**(联邦法规下的机场主计划,PDF 图),或 Territory Plan 2023 的相关条文(未实测)。skill 做法=给出到机场距离提示 + 指向 Master Plan。
- 测试地址 Kaleen 离 Canberra Airport 较远(位于 Belconnen,北部),不会在 ANEF 20 内(**属常识判断,非实测**)。

---

## 9. 政策红利(与住宅增值潜力相关的现行政策)

**来源:ACT Revenue Office 官方页面(2026-10-03 取得原文)+ 搜索摘要中 ACT 政府新闻稿标题。**

### 9a RZ1 dual occupancy(Territory Plan 2023)
- 原文(https://www.revenue.act.gov.au/home-buyer-assistance/rz1-unit-duty-exemption-scheme ):"The Territory Plan 2023 allows dual occupancy developments on residential suburban zoned blocks (RZ1) of 800m2 with a modest second dwelling of 120m2 (excluding the garage). The block can then be unit titled under the Unit Titles Act 2001 to allow the second dwelling to be individually sold."
- 生效:Territory Plan 2023 / 新规划体系 **2023-11-27 起**(页面中的优惠起算日 "From 27 November 2023";新体系启动日期同日,据 planning.act.gov.au FAQ 搜索摘要,**FAQ 原文未直接核实**)。
- **测试地址相关性**:30 Diamantina Crescent 是 RZ1、BLOCK_DERIVED_AREA **928 m²(>800 m²)**——**面积门槛满足**;但是否可建/可分割还取决于 Territory Plan 2023 的其他规则(site coverage、soft landscaping、树木、overlay、租约 purpose clause、DA)——**本说明不下结论**。

### 9b RZ1 Unit Duty Exemption(首次转让 unit-titled 的 stamp duty 豁免)
- 原文:"From 27 November 2023 until 30 June 2026, the ACT Government is offering a duty exemption for the first transfer of unit titled properties on RZ1 blocks up to a prescribed dutiable value that have been newly subdivided under the Unit Titles Act 2001."
- 页面分期门槛:2023-11-27 至 2024-06-30 ≤ $800,000;2024-07-01 至 2025-06-30 ≤ $1,000,000;**2025-07-01 至 2026-06-30 ≤ $1,020,000**(合同需在该期内签订并交换)。
- **⚠️ 状态**:页面写明的截止日 **2026-06-30 已过(今天 2026-10-03)**;本次**未找到延期/续期的官方公告**,请在报告中标「到期,是否延续需查 revenue.act.gov.au」。

### 9c RZ1 LVC 部分豁免(Lease Variation Charge,租约变更费)
- 原文(https://www.revenue.act.gov.au/lvc/rz1-lvc-partial-waiver ):"From 27 November 2023 to 30 June 2026, owners can choose whether their LVC to amend the maximum number of dwellings on their RZ1 block is either: the codified values or 75 per cent of the value uplift as measured by an accredited valuer, whichever is lower." 资格:DA 须在 "27 November 2023 to 30 June 2026" 期间提交;豁免申请须在 LVC 评估通知日起 60 天内提交。
- **⚠️ 状态**:同样**到期日 2026-06-30 已过**,本次未找到延期公告。

### 9d 其它(未核实)
- ACT 的 "Missing Middle"、Gungahlin/City 的 mixed-use 重划等**未取得官方原文,不写入**。

---

## 测试地址实测结果汇总表(30 Diamantina Crescent, Kaleen ACT)

| 检查项 | 数据源 | 状态 | 测试地址返回值 |
|---|---|---|---|
| 地址→坐标 | ACTGOV_ADDRESSES/0 | ✅ | 149.10096628, -35.22851825;Section 110 Block 23 |
| 地块 | ACTGOV_BLOCKS/0 | ✅ | BLOCK_KEY 55531100023;928 m²;VOLUME_FOLIO 630:14;REGISTERED |
| unit title | ACTGOV_UNIT/0 + 地址层 | ✅ | 本址非 unit(对照 24A Burnett St = UP1562) |
| Crown lease 条款 | — | ⚠️/❌ | 租期/purpose clause/LVC 免费图层无;需 Land Titles Register(未实测) |
| 分区 | block 层 + TP_LAND_USE_ZONE/1 | ✅ | RZ1 Suburban(旧 gazettal 元数据 TP 2008) |
| Overlays | TP_OVERLAY_ZONE_POLY/0 | ✅(旧体系) | 无;2023 新 overlay 服务未找到 |
| Heritage | Heritage_Register/1 | ✅ | 无 |
| 洪水 | FLOOD_EXTENT/0 | ✅(仅 1% AEP 范围) | 范围外(0 条) |
| 山火 | Bushfire_Prone_Area_Overview_2026/0 | ✅ | 非 BPA |
| 滑坡 | — | ❌ | 无免费源 |
| ASS / 海岸 | — | ❌(不适用) | — |
| 盐渍 HGL | HGL_Hydrogeological_Landscapes/0 | ✅ | Bruce,Moderate |
| 环境噪声分区 | Noise_Zones/6 | ✅ | Zone G(非 ANEF) |
| UV 估价 | Access Canberra UV register | ⚠️(免费,需浏览器) | 2026 UV 已于 2026-06-23 厘定;未取得本址数值 |
| DA | ACTIVE/COMPLETED_DEVELOPMENT_APPLICATIONS | ✅ | 本块 DA 200913874(2009 Approval Conditional);邻地 202443004(2024-11-13 在审) |
| 车流量 | — | ❌ | 无 AADT;仅行程时间统计 |
| 铁路/轻轨 | ACTGOV_RAILWAY/0 | ✅(机制) | 测试地址未专门 envelope 复核 |
| ANEF | — | ⚠️ | 需 Canberra Airport Master Plan |
| 政策(RZ1 dual occ) | revenue.act.gov.au | ✅原文;⚠️优惠已到期 | RZ1 ≥800 m² 可 dual occ(本址 928 m²);duty 与 LVC 优惠至 2026-06-30(已过) |

## 未解决 / 存疑清单(ACT)

1. **UV 数值**:官方免费 register 已确认存在,但表单是 Salesforce LWC(无法 curl);未取得测试块 UV。需浏览器或人工。
2. **Crown lease 细节**(起讫、purpose clause、租金)无免费图层;ACT Land Titles Register 是否收费/是否有免费摘要**未实测**。
3. **Territory Plan 2023 新体系 overlay**:`ACTGOV_TP_OVERLAY_ZONE_POLY` 看起来是旧 overlay;2023 体系 overlay(含 heritage precinct、tree、flood、bushfire 等)是否有要素服务**未找到**。
4. **RZ1 优惠(duty exemption、LVC partial waiver)** 页面写的截止日 2026-06-30 已过,**延期状态未核实**。
5. **Territory Plan 2023 的启动日期 2023-11-27**:来自搜索摘要,planning.act.gov.au FAQ 原文未直接取得;revenue.act.gov.au 页只证明优惠起算日 27 Nov 2023。
6. **车流量**:无 AADT 开放数据(TCCS 年报是否有未验证)。
7. **洪水**:只有 1% AEP 模型范围;无深度/hazard;模型外区域风险无法判断。
8. **土壤景观图层**返回值与位置明显不符(疑精度/匹配问题),不入报告。
9. **ANEF**:仅 Master Plan PDF,无接口。
10. 地址层无 SUBURB 字段(用 DIVISION),且存在重复/历史地址;地址标准化(大写、全称街道类型)是调用成功的前提。
11. `Bushfire_Prone_Area_Details_2026`、`Flood_Boundary`、`DAFINDER_PREDA` 等服务**仅发现未测**。
