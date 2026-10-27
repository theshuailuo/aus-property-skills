# VIC(Victoria)州适配说明 — 澳洲住宅物业尽调 skill

实测日期:2026-10-03(所有「实测通过」均为当天 curl 真实返回)。
测试地址:
- A = 2/56 Hemmings Street, Dandenong VIC 3175(townhouse/unit,主测)
- B = 2/53 Spencer Road, Camberwell VIC 3124

只用官方、免费、公开源。无登录、无 API key。

状态图例:✅ 实测通过 / ⚠️ 需浏览器人工或只有部分可得 / ❌ 无免费源 / 「未实测」= 本次没跑过,别当成事实。

---

## 0. 通用约定与坑(先读)

**两个官方服务器**
1. `https://opendata.maps.vic.gov.au/geoserver/wfs`(DEECA/DTP 的 Vicmap Open Data GeoServer,WFS 2.0.0,GeoJSON 输出)。图层命名空间 `open-data-platform:`。实测 GetCapabilities 共 502 个图层。
2. `https://plan-gis.mapshare.vic.gov.au/arcgis/rest/services/Planning/...`(DTP 规划部 VicPlan 背后的 ArcGIS Server 10.81 MapServer,REST `/query`)。

**坐标系坑(最重要)**
- GeoServer 默认 CRS = EPSG:7844(GDA2020)。WFS 2.0.0 + 7844 是**纬度在前**的轴序。直接写 `POINT(lon lat)` 会**静默返回 0 条**(不是报错)。
- 实测可用的两种写法(二选一):
  - `INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))` ← **本文统一用这个**,经度在前。
  - `INTERSECTS(geom,POINT({lat} {lon}))` ← 纬度在前,也通。
- 返回的 GeoJSON 坐标是 `[lon, lat]`(经度在前)。
- 距离查询:`DWITHIN(geom,SRID=7844;POINT({lon} {lat}),{米},meters)`(实测通)。`degrees` 写法会报 CQL 解析错误。
- ArcGIS 查询用 `inSR=4283`(GDA94,与 GDA2020 在点查精度上差 ~1.8 m,点查可忽略)。

**curl 模板(Git Bash;PowerShell 请用 `curl.exe`)**
```bash
wfs(){ # $1=layer  $2=CQL  [$3=额外参数 如 propertyName=a,b]
curl -s -m 90 -G "https://opendata.maps.vic.gov.au/geoserver/wfs" \
 --data-urlencode "service=WFS" --data-urlencode "version=2.0.0" --data-urlencode "request=GetFeature" \
 --data-urlencode "outputFormat=application/json" --data-urlencode "typeNames=open-data-platform:$1" \
 --data-urlencode "CQL_FILTER=$2" ${3:+--data-urlencode "$3"}; }

arc(){ # $1=Planning 下服务名 $2=图层号 $3=lon $4=lat  (可加 distance)
curl -s -m 60 -G "https://plan-gis.mapshare.vic.gov.au/arcgis/rest/services/Planning/$1/MapServer/$2/query" \
 --data-urlencode "geometry={\"x\":$3,\"y\":$4,\"spatialReference\":{\"wkid\":4283}}" \
 --data-urlencode "geometryType=esriGeometryPoint" --data-urlencode "inSR=4283" \
 --data-urlencode "spatialRel=esriSpatialRelIntersects" --data-urlencode "outFields=*" \
 --data-urlencode "returnGeometry=false" --data-urlencode "f=json"; }
```

**被封的站(别直连)**:`www.land.vic.gov.au` 与 `www.planning.vic.gov.au` 用 curl 直连返回 403(Cloudflare JS 挑战)。读正文改走 `https://r.jina.ai/<原 URL>`(实测 200,能取到正文)。`planning-schemes.app.planning.vic.gov.au`(条文 ordinance)是单页应用,jina 也只拿到空壳,条文要浏览器看。

---

## 1. 地址 → 坐标 → 地块(SPI / lot-plan / 面积 / 边界)/ 是否 strata

**数据源**:Vicmap Address(`address`)、Vicmap Property/Parcel 视图(`v_parcel_mp` 地块、`v_property_mp` 产权属性)。出处:data.vic.gov.au / opendata.maps.vic.gov.au 的 Vicmap Open Data(DEECA/DTP)。

### 1a 地址 → 坐标 + property_pfi ✅
```bash
wfs address "ezi_address='{大写标准地址}'"   # 例: '2/56 HEMMINGS STREET DANDENONG 3175'
# 模糊: "ezi_address ILIKE '%56 HEMMINGS STREET DANDENONG%'"  (一次列出整栋所有单元)
```
返回字段:`geometry.coordinates=[lon,lat]`(地址点);`pfi`(地址 ID)、`property_pfi`(产权属性 ID,用来关联);`blg_unit_type/blg_unit_id_1`(UNIT / 2);`lga_code`(326=Greater Dandenong,307=Boroondara);`geocode_feature`(V=属性点)。
- ⚠ 字段名是 `ezi_address`,不是 `ezi_add`(后者报 Illegal property name)。
- 地址必须是 Vicmap 标准大写拼写;用户输入要先标准化(街型 STREET/ROAD、郊区、邮编)。找不到就用 ILIKE 去掉单元号模糊搜。
- 备用路线(ArcGIS):`.../Planning/VicPlan_PropertyAndParcel/MapServer/2/query?where=EZI_ADDRESS LIKE '2/56 HEMMINGS STREET%'`,注意 ArcGIS 版字段名是 `EZI_ADDRESS`(写成 EZI_ADD 返回 400)。此备用 where 本次**未重测成功**(我第一次用错字段名),只验证了图层字段表。

实测:
- A:`[145.204018, -37.982691]`,property_pfi `426082216`,LGA 326。
- B:`[145.070654, -37.828286]`,property_pfi `211678380`,LGA 307。
- A 整栋 `56 HEMMINGS STREET` 列出 1/..5/ 共 5 个单元地址。

### 1b 坐标 → 地块 lot/plan(SPI)✅
```bash
wfs v_parcel_mp "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))"
# 只要字段: 第3参数 propertyName=parcel_spi,parcel_plan_number,parcel_lot_number,parcel_status,parcel_reg_date
```
读法:
- `parcel_spi` = Standard Parcel Identifier,格式 `{lot}\{plan}`,如 `2\PS727115`。
- `parcel_plan_number`=PS727115,`parcel_lot_number`=2,`parcel_status`=A(active)、`parcel_reg_date`=分割图注册日。
- `parcel_pfi` 可经 `parcel_property`(`wfs parcel_property "property_pfi='{pfi}'"`)与产权属性关联。
- 备用路线(ArcGIS,实测通):`arc VicPlan_PropertyAndParcel 4 {lon} {lat}`(字段大写,同内容)。

实测:
- A:SPI `2\PS727115`,注册 2020-01-08,LGA 326。
- B:SPI `2\PS618333`,注册 2008-11-11,LGA 307。

### 1c 地块面积与边界多边形 ✅(自己算)
- Vicmap 地块图层**没有面积字段**。边界多边形就是返回的 `geometry`(MultiPolygon,GDA2020 经纬度)。
- 要得到准确平方米:请求时加 `srsName=EPSG:7855`(GDA2020 / MGA zone 55,单位米),再用鞋带公式算。本次用 7855 实算。
```bash
wfs v_parcel_mp "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))" "srsName=EPSG:7855"   # 返回米制坐标
wfs v_property_mp "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))" "srsName=EPSG:7855"  # 含 base property 外框
```
实测面积(米制鞋带公式):
| | 该 lot 地块 | base property(整块开发用地) |
|---|---|---|
| A Hemmings | **89.0 m²** | **829.8 m²** |
| B Spencer | **244.3 m²** | **670.6 m²** |

读法/⚠️:
- townhouse 在 PS 分割图里的 lot 很多只框住建筑本体(A 的 89 m² 明显不是可用地),庭院/车道可能属于公共产权或别的 lot。**不要把 lot 面积当「土地面积」直接喂给地价/估价逻辑**。整块用地面积看 base property(`v_property_mp` 里 `prop_property_type='G'` / `propv_graphic_type='B'` 的多边形);每个 lot 真实面积以 Certificate of Title / 分割图为准(Landata 付费,本说明不覆盖)。
- `prop_property_type` 的 O / G 官方含义**本次未在官方文档核到**;按数据行为推断:O=单一产权属性,G=把多个单元圈起来的整体(base)属性。标「推断」。
- 同一点会返回 2 个 property(单元自己 + base),写脚本要按 `propv_graphic_type`(P/B)分开。

### 1d 判断 strata / Owners Corporation ✅
官方出处(Land Victoria 术语表,实测抓取):
- 「Plan of subdivision (LP or PS)」= 把一块地分成可单独出售的 lot。
- 「Plan of consolidation (CP or PC)」= 把相邻地块合并。
- 「Owners corporation」= 负责维护公共产权(common property);**公共产权在 plan of subdivision 上界定**;「most blocks of flats or units have an owners corporation」。
- 出处:https://www.land.vic.gov.au/land-registration/first-time-here/land-registration-glossary (经 jina 读取)。
- SP(Strata Plan,旧制)、RP/TP 等其它前缀的含义,**本次未在官方页面核到**,不要写死;遇到 PS/LP 以外的前缀,标「需人工查 Landata 分割图」。

**实用判据(实测,推断类)**:查同一分割图下所有 lot:
```bash
wfs v_parcel_mp "parcel_plan_number='{PS/LP号}'" "propertyName=parcel_spi,parcel_lot_number,parcel_status"
```
- 出现 `CM1`(或 `CM…`)lot = 公共产权(common property)lot ⇒ 该分割图有 owners corporation ⇒ 实务上按 strata/OC 物业处理。
- 实测 A:`PS727115` 共 6 条 = lot 1–5 + `CM1`;B:`PS618333` = lot 1、2 + `CM1`。
- 「CM=common property」是从数据形态推断,官方 Vicmap 产品说明未核。**判决前仍需 title/分割图确认 OC 费率与规则(OC certificate 付费)**。
- 注:A、B 的 plan 前缀都是 PS(Plan of Subdivision),不是 SP;VIC 现代 townhouse/unit 绝大多数是 PS + OC。

**状态:✅**
**A 结论**:Lot 2 on PS727115,5 lot + CM1 公共产权 ⇒ 有 OC;**B 结论**:Lot 2 on PS618333,2 lot + CM1 ⇒ 有 OC(小型 2 户 OC)。

---

## 2. 规划分区(Zone)+ 全部规划 Overlay

**数据源**:Vicmap Planning(WFS `plan_zone`、`plan_overlay`),以及 VicPlan 的 ArcGIS 服务。出处:Planning Victoria VicPlan https://www.planning.vic.gov.au/planning-schemes/using-vicplan 。

### 2a WFS 路线 ✅(主路线)
```bash
wfs plan_zone    "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))"
wfs plan_overlay "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))"   # 返回 0..N 条,每条一个 overlay
```
字段读法:`zone_code`(HCTZ2、HO701、SBO…)、`zone_description`、`scheme_code`(ZN/HO/DDO…)、`lga`、`gaz_begin_date`(该控制生效/刊宪日期)。
- overlay 返回多条时每条 `zone_code` 就是一个 overlay(带 schedule 号,如 DDO8、SLO23、HO701)。无 overlay = 返回 0 条。

### 2b ArcGIS 路线 ✅(交叉验证)
```bash
arc Vicplan_PlanningSchemeZones      0 {lon} {lat}   # 图层0=All Zones
arc Vicplan_PlanningSchemeOverlays   0 {lon} {lat}   # 图层0=All Overlays
```
字段:`ZONE_CODE`、`ZONE_DESCRIPTION`、`ZONE_CODE_GROUP_LABEL`(如 "HCTZ - Housing Choice and Transport Zone")、`GAZ_BEGIN_DATE`(毫秒时间戳)。
- Overlay 分图层号(实测读自服务元数据):3 ESO,4 SLO,5 VPO,7 DDO,8 DPO,9 HO,10 IPO,11 NCO,35 BFO,34 BAO,13 EMO,14 FO,15 LSIO,16 SBO,17 SMO,18 SRO,19 BMO,21 SCO,22 AEO,23 CLPO,24 DCPO,25 EAO,26 ICO,27 MAEO,28 PAO,29 PO,30 RO,31 RXO,32 RFO,33 PSB。
- Zone 图层 57 = HCTZ(新增区)、58 = PRZ;6 RGZ、7 NRZ、8 GRZ 等。

### 2c 交叉验证 / 覆盖度验证 ✅
- WFS 与 ArcGIS 对 A、B 的 zone 与 overlay 完全一致。
- 阳性对照(确认 overlay 层真能返回多类):点 (145.52,-37.65)(Yarra Ranges)两条路线都返回 DDO8 + BMO + SLO23 + SLO6 + LSIO;点 (144.8995,-37.7745)(Moonee Valley)ArcGIS 返回 DCPO1 + DDO1 + SLO2 + LSIO1。证明 BMO、LSIO、DCPO 等类别都在该图层里。

### 2d 实测结果
| | Zone | Overlays(在 lot 点/lot 多边形/base property 多边形上) |
|---|---|---|
| A Hemmings | **HCTZ2** — Housing Choice and Transport Zone Schedule 2(Greater Dandenong),gaz_begin 2026-07-22 | **无**(点查 0 条;lot 多边形相交 0 条;base property 多边形相交 0 条) |
| B Spencer | **HCTZ2**(Boroondara),gaz_begin 2026-07-22 | **HO701 Heritage Overlay**(gaz_begin 2019-08-30);仅此一条 |

### 2e 判读注意
- 多边形相交比点查更稳:用 `v_parcel_mp` 取多边形转 WKT,`INTERSECTS(geom,SRID=7844;POLYGON((lon lat,...)))`,可发现点查漏掉的「地块一角」被覆盖的 overlay。本次 A、B 点查与多边形相交结果一致。
- 附近但不在地块上的 overlay 也要看:B 点周边 150 m 内有 SBO 和 HO159(不在本地块);Spencer Rd 邻居的规划许可(见 §7)描述里有「Special Building Overlay」,说明该街局部有积水/排水风险。用 `DWITHIN(...,150,meters)` 可列出。A 周边 300 m 有 HO48、HO10、SCO10、SCO11,不在本地块。
- **Hemmings、Spencer 的 HCTZ2 是 2026-07-22 才生效的新分区**(见 §9);条文高度、车位、住宅标准要读 Greater Dandenong / Boroondara 规划条文 Clause 32.10 + Schedule 2。条文页是单页应用,本次**无法自动取文**,标 ⚠️ 需浏览器:`https://planning-schemes.app.planning.vic.gov.au/Greater%20Dandenong/ordinance/32.10` 与 `.../Boroondara/ordinance/32.10`(两个 URL 未实测渲染)。
- B 同时有 HCTZ + HO:官方 PPN91 说明 HCTZ 可叠加 HO,「responsible authority will assess individual development proposals against both the HCTZ and the HO」(见 §9)。**HO 内拆建/加建大概率仍需 heritage 许可,别按 HCTZ 增值潜力直接算**。
- Overlay schedule 的具体内容(如 HO701 保护什么、DDO 限高)只给 schedule 号,条文要人工读。
- VicPlan 的 web 界面有 Planning Property Report(官方按地址出 PDF),本次**未测**其自动化接口。

**状态:✅**

---

## 3. 洪水(overlay 之外的官方洪水范围)

### 3a 规划洪水 overlay(官方「1%AEP / 1-in-100」)✅
- 官方说明(Melbourne Water,实测抓取):「Flood planning controls are based on the extent of flooding resulting from a 1 in 100 year flood event」,洪水 overlay 包括 SBO(雨水/内涝)、LSIO(河道/海岸淹没)、FO(行洪道)、UFZ(区域)。出处:https://www.melbournewater.com.au/building-and-works/flooding-information-and-advice/flood-planning-controls-explained (页面更新 2 Oct 2025)。
- 查询 = §2 的 `plan_overlay` / ArcGIS 图层 14 FO、15 LSIO、16 SBO、32 RFO,以及 zone 图层 44 UFZ。命令:
```bash
wfs plan_overlay "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))" "propertyName=zone_code,zone_description"   # 看有没有 SBO/LSIO/FO/RFO
arc Vicplan_PlanningSchemeOverlays 16 {lon} {lat}    # 只查 SBO;换成 15 查 LSIO,14 查 FO
```
- 实测:A **无**洪水 overlay;B **无**(但 150 m 内有 SBO,见 §2e)。

### 3b 历史洪水事件范围 ✅(只是事件,不是概率范围)
- `vic_flood_history_public`(Emergency Management Victoria,「Victorian Flood History October 2022 Event Public」)。只有 2022 年 10 月事件的观测范围。
```bash
wfs vic_flood_history_public "DWITHIN(geom,SRID=7844;POINT({lon} {lat}),500,meters)" "propertyName=subtype,flood_obs_,obs_date,label"
```
- 本次对 A、B 未跑该图层(**未实测**,仅确认图层存在及字段名)。别当成官方 1% 范围。

### 3c 点位洪水高程 / 洪水证书 ⚠️ 收费
- 官方 Melbourne Water Property Flood Level Certificate:给出 1% AEP 的预估最高水位(m AHD),**$57.47**(页面所示,最多 14 天回复,证书 3 个月有效)。出处:https://www.melbournewater.com.au/building-and-works/apply-to-build-or-develop/property-flood-level-certificate 。付费且只对有洪水 overlay 的产权。本说明**不使用**,只作人工提示。
- 官方 flood 页面强调 VicPlan 仅作参考(「VicPlan is a guide only」)。

### 3d 找不到的东西 ❌
- 试了三条路均无「全州 1-in-100 洪水范围」免费开放 API:(1)data.vic CKAN 搜 flood(22 条,仅 2022 事件、Port Fairy/Western Port 海平面、Casey 防洪堤等局部数据);(2)Melbourne Water ArcGIS Hub 搜 flood(4 条,全是集水区/湿地/水道中线,无淹没范围);(3)opendata.maps.vic.gov.au WFS 502 个图层里只有 `vic_flood_history_public`。
- 结论:**VIC 官方免费可机读的洪水风险 = 规划 overlay(SBO/LSIO/FO)**;精确水位只有付费证书。

---

## 4. 山火:Bushfire Prone Area(BPA)+ BMO

### 4a BPA ✅
```bash
wfs bushfire_prone_area "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))"
arc VicPlan_Bushfire 1 {lon} {lat}      # 备用路线(ArcGIS 图层1=BPA,0=BMO,2=BPA History)
```
字段:`lga_name`、`plan_number`(如 LEGL./25-138)、`gazettal_date`(10/07/2025)。**返回 0 条 = 不在 BPA**。
- 阳性对照:(145.52,-37.65) → BPA 返回 `LEGL./25-138`(YARRA RANGES,gazette 10/07/2025,约 242,306 ha),同点 BMO 也命中。

### 4b BMO ✅
```bash
wfs plan_overlay "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))" "propertyName=zone_code"   # 看是否有 BMO
arc VicPlan_Bushfire 0 {lon} {lat}
```
### 4c 实测:A 与 B 均**不在 BPA、无 BMO**(WFS + ArcGIS 两路都 0 条;多边形相交也 0)。

判读:BPA 是建筑法规(BAL)触发区;BMO 是规划 overlay(需要许可+CFA 参照)。BPA 内不一定有 BMO。官方文档链接未实测,其业务含义按常识写,落报告前由人工复核。

---

## 5. 滑坡 / 酸性硫酸盐土(CASS)/ 污染场地 / 矿区 / 其它

### 5a 滑坡 / 侵蚀
- 官方免费机读源只有 **EMO(Erosion Management Overlay)**,即 §2 的 overlay(ArcGIS 图层 13)。A、B 都没有。
- 另试两条路找全州滑坡易发图层:data.vic CKAN 搜 landslide / landslip(无相关);WFS 502 图层名里无 slip/slide。**判定:无免费全州滑坡易发度图层**(❌),只能看 EMO。

### 5b 沿海酸性硫酸盐土 CASS ✅(仅沿海)
```bash
wfs coastal_acid_sulphate_soils "INTERSECTS(geom,SRID=7844;POINT({lon} {lat}))"
```
字段:`prospectiv`(Prospective / Made land / Water)、`area_ha`。全图层仅 910 个多边形,只覆盖沿海带。**返回 0 条 = 不在沿海 CASS 范围**(不是「没有酸性硫酸盐土」)。
- 阳性对照:(144.583119,-38.274286) → 返回 Made land / Prospective / Water 三类多边形。
- 实测:A、B 均 0 条。
- 注:这是 CASS(沿海),内陆的酸性硫酸盐土 / 其它土壤风险**本次无免费图层**。

### 5c 污染场地:EPA Priority Sites Register(PSR)✅
```bash
wfs psr_point   "DWITHIN(geom,SRID=7844;POINT({lon} {lat}),{米},meters)"
wfs psr_polygon "DWITHIN(geom,SRID=7844;POINT({lon} {lat}),{米},meters)"
```
字段:`address`、`issue`、`psr_description`(如 Current industrial site)、`psr_management`(如 Requires assessment and/or clean up)、`notice_number`、`data_extracted_on`。数据抽取日 2026-10-03。
- 阳性对照/实测:A 500 m 与 2 km 内 0 条,5 km 内 1 条(80-82 Ordish Road Dandenong South,Current industrial site,EAN-00009303-1);B 500 m 内 0 条,3 km 内 1 条(150 Union Road Surrey Hills,chemical storage facility,EAN-00006454-2)。
- 相关图层(实测 500 m 内均 0 条,未做阳性对照):`vlr_point`/`vlr_polygon`(Victorian Landfill Register)、`gqruz_polygon`(地下水限制使用区)。另有 `epa_licence_point/polygon`(EPA 牌照,**未实测**)。
- PSR 只列「被官方点名的场地」,**不能证明某块地没污染**;规划上的 EAO(Environmental Audit Overlay)在 §2 overlay 里,A、B 均无。

### 5d 矿区 / 采石
- `former_mining_features_crown`(仅皇家地)A、B 1 km 内 0 条;ArcGIS `Extractive_Industry_Work_Authorities`(图层 0 current、1 application、2 EIIA)500 m 内 0 条。**未做阳性对照**。

### 5e 文化遗产
- VicPlan_Heritage:图层 2 Heritage Register、1 Heritage Inventory(考古)、3 Aboriginal Cultural Heritage Sensitivity;WFS `heritage_register`、`heritage_inventory`。A、B 全部 0 条(**未做阳性对照**)。注意 HO(地方 heritage overlay)才是 B 的实际限制(§2)。

**状态:✅(CASS、PSR 有阳性对照);滑坡 ❌;矿区/文化遗产/垃圾填埋 ✅但无阳性对照**

---

## 6. 官方估价(逐地块地价 / site value / CIV)

**结论:❌ VIC 没有类似 NSW Valuer-General 逐地块地价的免费公开查询。**

证据:
1. Valuer-General Victoria 官方页「Valuations for rates and land tax」(经 jina 实测抓取,页面更新 07/07/26):只解释 Site Value(SV,仅土地)、Capital Improved Value(CIV)、Net Annual Value(NAV=住宅 5% CIV),估价每年 1 Jan 为基准,用于 council rates、land tax、ESVF;**页面没有公开按地址查询入口**,联系邮箱 valuation.authority@transport.vic.gov.au。出处 https://www.land.vic.gov.au/valuations/valuations-for-rate-and-land-tax 。
2. data.vic CKAN 搜 `capital improved value`(25 条)、`site value valuation`(35 条)、`rating valuation`(0 条):只有 SRO 的 Fire Services Property Levy 费率表、Land tax by municipality 汇总,**没有逐地块估价**。
3. Vicmap Property 里有 council 产权号 `prop_propnum`(A=497845,B=570380),它是向 council 要估价/评估记录的钥匙,**但估价本身不在开放数据里**。

可用的免费替代(**都是区域级,不是逐地块**):
- Valuer-General Victoria Property Sales Data / Victorian Property Sales Report(VPSR):按郊区的 house/unit/vacant land 中位价,季度发布(3/6/9/12 月),10 年郊区年度中位价;data.vic.gov.au 上有对应 XLS 数据集(例:`victorian-property-sales-report-median-unit-by-suburb`,CC BY 4.0,CKAN 修改日期 2026-09-29)。出处页:https://www.land.vic.gov.au/valuations/resources-and-reports/property-sales-data (页面更新 09/09/26;含 March 2026 季度报告,2026 年 9 月发布)。
- ⚠️ 实测:`land.vic.gov.au/__data/assets/excel_doc/...xls` 直连下载 403;CKAN 里只有 2023-12 季度那个链接是 web.archive 镜像。要最新季度须浏览器下载。本次**未下载解析**,也未取 Dandenong/Camberwell 的具体中位价。

付费/人工(不进自动流程):council rates notice、Landata property reports、council 的 Land Information Certificate。

---

## 7. 规划许可 / 开发活动(planning permit activity)

### 7a PPARS(州级 Planning Permit Activity Reporting)✅ 有延迟
- ArcGIS:`https://plan-gis.mapshare.vic.gov.au/arcgis/rest/services/Planning/PPARS/MapServer`:图层 1–8 = 财年 2022-23、2021-22、…、2015-16 的**逐申请点位**;图层 0 = Final outcome;图层 9 = 各 LGA 许可总数/总造价。出处:DTP/Planning Victoria 官方 ArcGIS 服务(规划部 PPARS 数据)。
```bash
curl -s -G "https://plan-gis.mapshare.vic.gov.au/arcgis/rest/services/Planning/PPARS/MapServer/{1..8}/query" \
 --data-urlencode "geometry={\"x\":{lon},\"y\":{lat},\"spatialReference\":{\"wkid\":4283}}" \
 --data-urlencode "geometryType=esriGeometryPoint" --data-urlencode "inSR=4283" \
 --data-urlencode "spatialRel=esriSpatialRelIntersects" --data-urlencode "distance=250" --data-urlencode "units=esriSRUnit_Meter" \
 --data-urlencode "outFields=APPLICATION_ID,ADDRESS,DATE_APPLICATION_RECEIVED,PROPOSED_USE_OR_DEVELOPMENT,NUMBER_OF_NEW_DWELLINGS,OUTCOME,OUTCOME_DATE,ESTIMATED_COST_OF_WORKS,VCAT_APPEAL" \
 --data-urlencode "returnGeometry=false" --data-urlencode "f=json"
```
(花括号 `{1..8}` 是循环占位:对 1 到 8 逐层各发一次。)
- 日期字段是毫秒时间戳,要转换。`OUTCOME` 例:Permit issued by a delegate of the RA / NOD issued by a delegate / Refusal / Withdrawn / Lapsed。
- 实测 A(250 m):多条,如 50 HEMMINGS STREET(gdanPLN21/0403,2021-07-20 申请,「development of five (5) double storey dwellings…」,NOD issued by a delegate,2022-06-08)、63 Hemmings Street(gdanPLN20/0166,4 套双层 dwellings,2021-02-04 发 permit)、17 Birdwood Avenue 等。说明本街有持续的 townhouse 开发活动。
- 实测 B(250 m):多条,几乎都是 Heritage Overlay 内的加建/拆除(如 47 Spencer Road boroPP21/0453,Partial demolition and alterations in a Heritage Overlay,Permit issued by a delegate);无大型多户开发。
- ⚠️ **数据只到 2022-23 财年**(图层最新=2022-2023),**不是实时**。2023 年 7 月以后的申请不在这里。
- 判读:同一申请可重复出现(同 APPLICATION_ID 多条),要去重;「NUMBER_OF_NEW_DWELLINGS」是净新增。

### 7b 实时/最新申请 ⚠️ 需 council 网站
- 试了:(1)CKAN 搜 planning permit(36 条,只有 City of Casey 的 Planning Permit Application Register 一类 council 自己开放的 CSV);(2)ArcGIS Planning 文件夹里除 PPARS 外有 `Planning_Scheme_Boundary`、`VicPlan_Scheme_Additional`(规划修正案 exhibited/historical,不是个案许可);(3)VicPlan 的「Exhibited Amendments」层。**没有全州实时 permit 接口**。
- 结论:最新申请只能到各 council 的 Planning Register 页面人工看(Greater Dandenong、Boroondara 页面 URL **未实测**)。
- 建筑许可(building permit)只有汇总统计:CKAN `building-permit-activity-data`(Building and Plumbing Commission,按月汇总,不含地址)。

---

## 8. 道路车流量(AADT)/ 铁路 / 机场噪音

### 8a AADT ✅(只覆盖 declared roads,且只到 2019)
- 数据:DTP「Historical Annual Average Daily Traffic Volume」(2001→2019),全部为 Victoria declared road network 的各方向路段。出处:https://discover.data.vic.gov.au/dataset/historical-annual-average-daily-traffic-volume (CC BY 4.0,CKAN 修改日期 2025-07-14),文件托管在 opendata.transport.vic.gov.au。
- 没有 API,只有每年一个 GeoJSON。2019 文件 32 MB,14,662 条 LineString:
```bash
# 先取 URL(CKAN API,稳定)
curl -s -G "https://discover.data.vic.gov.au/api/3/action/package_show" --data-urlencode "id=historical-annual-average-daily-traffic-volume"   # 找 name 含 2019 的 resource.url
curl -L -o aadt2019.geojson "https://opendata.transport.vic.gov.au/dataset/26fafd1a-8d59-4da0-93cd-29f371147d8f/resource/425799c9-658c-41cf-b9b0-6c9a145856cf/download/yearly_aadt_volume_2019.geojson"
# 然后本地算点到线最近距离(equirectangular 即可,本次用 python 脚本)
```
- ⚠ 手敲 URL 容易因资源 ID 抄错得 404;务必从 package_show 拿。
- 属性:`Road Name`、`Road Section Description`、`Travel Direction`、`Average Annual Daily Traffic Volume`、`Average Annual Daily Heavy Vehicle Volume`、`Percentage of Heavy Vehicles`、`Calculation Methodology`(Estimated/Actual)、`Calendar Year`。
- 实测:
  - A:最近 declared road = Jones Road(277 m):南行 4,500 / 北行 4,281;Railway Parade(303 m):3,532 / 3,793;Bennet Street(344 m):4,500。重车占比约 6%。
  - B:Prospect Hill Road(158 m):4,608(东西向各 4,608,重车 0);Riversdale Road(512 m):6,260;Stanhope Grove(525 m):9,408 / 9,185,重车 7%;Trafalgar Road(556 m):8,763 / 8,704。
- 判读:本街(Hemmings、Spencer)是本地街,**不在 declared network 内,没有 AADT**,只能用最近的主干路作参考。数据是 2019 年,与今天(2026)相差 7 年,且 2020–2021 疫情影响,只能作量级。
- 其它:DTP 的 Telemetry/TIRTL/Traffic Signal 计数是小时/分钟级站点数据(CKAN 有,未下载),不是 AADT,未实测。

### 8b 铁路 ✅
```bash
wfs tr_rail "DWITHIN(geom,SRID=7844;POINT({lon} {lat}),1500,meters)"            # 铁路线/侧线/桥,含 name、feature_type_code
wfs vmlite_tr_rail_station "DWITHIN(geom,SRID=7844;POINT({lon} {lat}),1500,meters)"  # 车站(name)
```
- 要自己算「点到每条线的最短距离」(WFS 不返回距离)。`feature_type_code`:railway / bridge_rail_o / rail_siding / tramway。**别把 rail_siding(车辆段侧线)当正线**。
- `tr_rail` 里有重复/被取代记录(`superceded_pfi`),取最近距离时要去重。
- 实测(本次用 python 点到线计算):
  - A:Dandenong 车辆段侧线 318 m;**Pakenham Line 327 m**;Dandenong 站 **940 m**(属 vmlite 层);Dandenong 维修侧线 801 m。
  - B:**Alamein Line 49 m**(!);Lilydale Line 310 m;有轨电车线 511 m;Camberwell 站 1,069 m。
- ⚠️ 距离是到线的直线距离,不含列车频率、地势、围挡;**B 离 Alamein 线 49 m 是重大噪音/振动提示**,但是否有地下/路堑未知,需现场看。道路路网:VicPlan_Transport 服务有 PPTN、Rail corridor 等图层(图层号见元数据,**本次未查点**)。

### 8c 机场:ANEF / Airport Environs Overlay ✅(只覆盖 Melbourne Airport)
- 官方 ArcGIS:`Planning/Melbourne_Airport_Master_Plan_2022_VicPlan/MapServer`,图层 12 = ANEF 20、11 = ANEF 25、10 = ANEF 30、9 = ANEF 35,图层 3/4/5 = N65/N60/N60 Night 等「Number Above」噪音线。字段 `ANEF` 为等值线数值。
```bash
arc Melbourne_Airport_Master_Plan_2022_VicPlan 12 {lon} {lat}   # 12/11/10/9 各查一次;任一有返回即在该 ANEF 线内
arc Vicplan_PlanningSchemeOverlays 22 {lon} {lat}               # AEO
arc Vicplan_PlanningSchemeOverlays 27 {lon} {lat}               # MAEO (Melbourne Airport Environs Overlay)
```
- 注意 ANEF 图层可能是「环形」嵌套多边形,按各层独立点查再取最高值。
- 阳性对照:点 (144.8420,-37.6420) 在图层 11 返回 `ANEF=25`。
- 实测:A、B 的 ANEF 20–35、N60/N65 图层、AEO、MAEO 全部 0 条 ⇒ 不受 Melbourne Airport 噪音等值线影响。
- ⚠️ 只覆盖 Melbourne (Tullamarine) 机场。Essendon、Moorabbin、Avalon 等**未实测**(AEO 在 overlay 层可能有)。

---

## 9. 政策红利(只认官方 planning.vic.gov.au / legislation 原文)

引用页面经 jina 取正文(planning.vic.gov.au 直连被封)。「页面更新日」取自页面自己标的 Last updated。

### 9a Housing Choice and Transport Zone(HCTZ)与 Train and Tram Zone Activity Centres Program ⭐对两个测试地址直接相关
- 官方页:https://www.planning.vic.gov.au/guides-and-resources/strategies-and-initiatives/activity-centres-program/about-activity-centres/about-our-plans (Published October 2026,Last updated 02 October 2026)。
  - 「The new Housing Choice and Transport Zone (HCTZ) has been developed to enable a diversity of housing in the catchments, and other well-serviced locations…」
  - 全 60 个 train and tram zone activity centres 的计划已完成;大多数中心分 core 与 catchment;catchment 约核心起 800 m / 10 分钟步行。
  - 官方表(摘):Inner catchment「Up to four storeys, and up to six storeys on blocks larger than 1000m2」;Outer catchment「Up to three storeys, and up to four storeys on blocks larger than 1000m2」;Core 多为 6–16 层。
  - catchment 内 HCTZ 的 notice/review「depend on the provisions of the residential development codes. In most cases, notice requirements remain」。
- 官方 timeline 页(Last updated 02 October 2026):https://www.planning.vic.gov.au/guides-and-resources/strategies-and-initiatives/train-and-tram-zone-activity-centres/program-timeline-and-milestones
  - 10 个 pilot 中心 2025 年 4 月定稿;25 个 Stage 1 中心 2026 年 3 月定稿;23 个 Stage 2 中心 2026 年 7 月定稿;2 个内墨尔本中心 2026 年 8 月定稿。
  - Infrastructure Contributions Plans(ICP)计划 2026 年末分阶段刊宪;**ICP 收费 2027 年 1 月起(10 个 pilot 中心)、2027 年 7 月起(其余 49 个)**。⇒ 开发成本提示:2027 起这些中心范围内开发可能要交基础设施费(具体金额本次未查)。
- 测试地址印证:A、B 的 `plan_zone` 数据显示 `HCTZ2`,`gaz_begin_date = 2026-07-22T00:00:00Z`(与官方「Stage 2 于 2026 年 7 月定稿」吻合)。**但**官方「找中心」表里 Camberwell Junction 标 Pilot(Boroondara),而 B 的 HCTZ2 生效日是 2026-07-22,说明 B 的 HCTZ 可能是 pilot 后续修正案落地,具体修正案编号**未核**;A 对应哪个 activity centre / Stage 也**未核**(表分页,本次只读到首页)。
- 条文(PPN91 Using the residential zones,官方,https://www.planning.vic.gov.au/guides-and-resources/guides/planning-practice-notes/using-the-residential-zones ):
  - 「The Housing Choice and Transport Zone promotes housing growth of 3 to 6 storeys and supports lot consolidation by allowing higher building heights on larger sites. Maximum building heights are fixed by the zone and cannot be varied through a schedule to the zone.」
  - 「The HCTZ may apply to land affected by a HO … the responsible authority will assess individual development proposals against both the HCTZ and the HO」(对 B 关键)。
  - 本页的页面更新日期本次**未取到**。
- ⚠️ HCTZ2 的具体高度上限、A/B 属 inner 还是 outer catchment、有无按地块面积放宽:**未取到**(ordinance 页面 SPA)。需浏览器看 Clause 32.10 与 Schedule 2,或 VicPlan 的 Planning Property Report。

### 9b Townhouse and Low-Rise Code(Clause 55 deemed-to-comply)
- 官方页:https://www.planning.vic.gov.au/guides-and-resources/guides/all-guides/residential-development/townhouse-and-low-rise-code (Page last updated 24/09/26)。
  - 「The deemed to comply standards will be approved on 6 March 2025 and commence operation on 31 March 2025.」(Amendment VC267)
  - 对 1–3 层的多 dwellings:Clause 55 在 RGZ、GRZ、NRZ、**HCTZ**、MUZ、TZ 内使用。
  - 满足所有适用标准时「there will be no third party right of appeal (objector appeal)」。
  - 2025 年 3 月 6 日前提交的申请按旧版 Clause 55 评估。
  - 「Subsequent updates were made to the Townhouse and Low-Rise Code on 24 September 2026 by Amendment VC315」(澄清/一致性,含 tree canopy)。
  - VicSmart(Amendment VC288):加第二套 dwelling、建两套新 dwelling、或把一块地分成两块更容易,「The changes came into effect on 16 October」——页面**没写年份**(未核,不要写死 2025)。
- 原文修正案页(单页应用,未实测渲染):planning-schemes.app.planning.vic.gov.au/Victoria Planning Provisions/amendments/VC267 、VC315、VC288。

### 9c Mid-Rise Code(Clause 57,4–6 层)
- 官方页:https://www.planning.vic.gov.au/guides-and-resources/guides/all-guides/residential-development/Mid-rise-code (Page last updated 17/04/26)。
  - 「introduced through Amendment VC300, gazetted on 19 March 2026. The requirements of the Mid-Rise Code commenced operation on 16 April 2026.」
  - Clause 57 适用于 MUZ、TZ(城市增长边界内墨尔本都会区)、RGZ、**HCTZ** 的 4–6 层。
  - 「The Mid-Rise Code does not remove other planning controls such as heritage overlays, flood controls or environmental requirements.」
  - 同样有第三方上诉豁免条款(细节未逐字核)。

### 9d Future Homes(Clause 53.24)——对 A、B 不适用
- 官方页:https://www.planning.vic.gov.au/guides-and-resources/strategies-and-initiatives/future-homes (Page last updated 04/09/26)。
  - 资格:「The land is in a General Residential Zone」且任一部分在火车站/已识别活动中心 800 m 内,且「not within a heritage overlay or neighbourhood character overlay」。
  - **A、B 都是 HCTZ,不是 GRZ ⇒ Future Homes 路径不适用**(除非分区变更);B 另有 HO。
  - 生效日期:本次从官方页**没读到**。曾见 Mansfield council 转载条文文件标 VC243、22/09/2023,属于非官方二手,**仅作线索,不引用**。

### 9e 与增值潜力的关系(判断,非官方原文)
- 两个测试地址都是 townhouse 一个 lot(A 89 m² lot、B 244 m² lot)位于 PS + OC 之下。HCTZ 释放的增值潜力主要属于「整块可合并用地的开发商」;单个 lot 的业主(strata 下)要改建需 OC 同意,**难以单独受益**。要评估必须看:整块用地(base property 829.8 m² / 670.6 m²)是否整体可再开发、OC 规则、heritage(B)。
- 本节为推断,供报告写「待核」。

---

## 10. 两个测试地址实测结果汇总表

| 检查项 | A:2/56 Hemmings St, Dandenong 3175 | B:2/53 Spencer Rd, Camberwell 3124 |
|---|---|---|
| 坐标(GDA2020 lon,lat) | 145.204018, -37.982691 | 145.070654, -37.828286 |
| LGA | Greater Dandenong (326) | Boroondara (307) |
| property_pfi / council propnum | 426082216 / 497845 | 211678380 / 570380 |
| SPI / 分割图 | 2\PS727115,注册 2020-01-08 | 2\PS618333,注册 2008-11-11 |
| lot 面积(7855 实算) | 89.0 m²(只框建筑,勿当土地面积) | 244.3 m² |
| base property 面积 | 829.8 m²(1–5 lot + CM1) | 670.6 m²(1–2 lot + CM1) |
| strata / OC | 有 CM1 公共产权 lot ⇒ OC(推断) | 同左 ⇒ OC(推断) |
| Zone | HCTZ2,gaz 2026-07-22 | HCTZ2,gaz 2026-07-22 |
| Overlays | 无 | HO701(gaz 2019-08-30) |
| 附近(非本地块)overlay | 300 m 内:HO48、HO10、SCO10、SCO11 | 150 m 内:SBO、HO159;300 m 内另有 HO688、HO722 |
| 洪水 overlay(SBO/LSIO/FO) | 无 | 无(邻近有 SBO) |
| BPA / BMO | 无 / 无 | 无 / 无 |
| CASS(沿海) | 不在 | 不在 |
| EPA PSR | 2 km 内无;5 km 内 1 处(Ordish Rd Dandenong South) | 500 m 内无;3 km 内 1 处(150 Union Rd Surrey Hills) |
| 官方逐地块估价 | ❌ 无 | ❌ 无 |
| 附近 permit(PPARS 至 2022-23) | 多户开发活跃(50 Hemmings 5 套 NOD 2022-06;63 Hemmings 4 套 permit 2021) | 以 HO 内加建/拆除为主,无大型多户 |
| 最近 declared road AADT(2019) | Jones Rd 277 m:4,281–4,500,重车 ~6% | Prospect Hill Rd 158 m:4,608;Stanhope Grove 525 m:9,185–9,408,重车 7% |
| 最近铁路 | Pakenham Line 327 m;Dandenong 站 940 m | **Alamein Line 49 m**;Lilydale Line 310 m;Camberwell 站 1,069 m |
| ANEF / AEO / MAEO | 无 | 无 |
| Future Homes 资格 | 不适用(HCTZ 非 GRZ) | 不适用(HCTZ 非 GRZ,且有 HO) |

---

## 11. 未解决 / 存疑清单

1. **HCTZ2 具体条文**(高度上限、inner/outer catchment 归属、车位、住宅标准、是否对大地块放宽)取不到:ordinance 页是 SPA。需浏览器打开各 council 的 Clause 32.10 / Schedule 2,或 VicPlan Planning Property Report。A 对应哪个 activity centre 与 stage、B 的 HCTZ 是 pilot 后修正案还是 stage 2,均未核。
2. **官方 Vicmap 产品说明**未核:`prop_property_type`(O/G)与 `CM` lot 的官方定义、`SP/RP/TP` 前缀含义。当前判据是数据形态推断(CM1=公共产权)。
3. **lot 面积 ≠ 土地面积**:A 的 89 m² 只框建筑。精确每 lot 面积要 Certificate of Title/分割图(付费 Landata)。
4. **洪水**:VIC 无免费全州 1-in-100 范围,只有规划 overlay。Melbourne Water 洪水证书付费 $57.47。`vic_flood_history_public`(2022 事件)本次未对 A、B 实跑。
5. **滑坡 / 内陆酸性硫酸盐土**:无免费图层(只能看 EMO)。
6. **估价**:无逐地块官方估价。VPSR 郊区中位价 XLS 直连 403(Cloudflare),需浏览器或存档镜像;本次未取到 Dandenong / Camberwell 具体中位价。
7. **PPARS 只到 2022-23 财年**,2023-07 之后的许可无免费接口,需 council register(Greater Dandenong、Boroondara 页面 URL 未实测)。
8. **AADT 只有 2019 年、只含 declared roads**;本地街无数据;2020 以后无开放数据。道路噪音需另行估算。
9. **B 离 Alamein Line 49 m**:噪音/振动判读需现场(是否路堑/隔音墙)和列车频率;本次未查 PPTN 频率。
10. **阳性对照缺失**:Heritage Register/Inventory/ACH sensitivity、矿区、VLR、GQRUZ、extractive 层——A、B 全 0 条,但未做阳性对照,不能排除图层/参数错误(WFS 通用写法已在别的层验证通)。`epa_licence_*` 未实测。
11. **其它机场**(Essendon、Moorabbin、Avalon)的 ANEF 未实测。
12. **政策**:VC288 VicSmart「16 October」年份未核;Future Homes(53.24)官方生效日没读到;PPN91 页面更新日未取到;Activity Centres ICP 具体费率未查;各 VC 修正案原文页(SPA)未渲染。
13. 官方站点 `land.vic.gov.au` / `planning.vic.gov.au` 对直连 curl 返回 403;文中官方引文均通过 r.jina.ai 读取正文。若 jina 失效,需浏览器人工打开原 URL。
14. 上述数据均为 2026-10-03 当日快照;规划 overlay 与 zone 每次修正案都会变,报告应写取数日期。
