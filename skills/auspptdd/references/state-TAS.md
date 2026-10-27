# Tasmania(TAS)辖区适配说明 · auspptdd

- 实测日期:2026-10-03(本机 curl / Python urllib / Browser pane)
- **测试地址**:116 Tolosa Street, Glenorchy TAS 7010(Glenorchy,Hobart 都会区住宅;PID 5397238)
- **测试坐标(WGS84,来自 LIST 地址点)**:lon = 147.26837358,lat = -42.84212759
- 官方数据平台:**the LIST**(Land Information System Tasmania,Tasmanian Government / NRE Tas),ArcGIS Server 10.91 根目录
  `https://services.thelist.tas.gov.au/arcgis/rest/services`(匿名可读,无需 key;图层版权标 CC BY 3.0 AU / © State of Tasmania)
- 全局注意:LIST 的 `Public/*` MapServer 都支持 `/{layer}/query` 点查(矢量层)。**栅格层(SES 洪水)不支持 query,只能用 `/identify`**。所有命令里 `{lon} {lat}` = WGS84 十进制度,`inSR=4326`。
- 全局注意:`returnGeometry=false` 可大幅减小返回;面积/边界要边界时改 `returnGeometry=true&outSR=4326`。

---

## 1. 地址 → 坐标 → 地块(lot/plan/folio、面积、边界、strata)

### 1a 地址 → 坐标(官方地址点)
- 来源:LIST `Public/SearchService/MapServer/7`「Address Geocodes」
  出处 URL:https://services.thelist.tas.gov.au/arcgis/rest/services/Public/SearchService/MapServer/7
- 命令(按街道/地址模糊找):
```bash
curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/SearchService/MapServer/7/query" \
  --data-urlencode "where=UPPER(ADDRESS) LIKE '%{STREET_NUMBER} {STREET NAME} {STREET TYPE} {LOCALITY}%'" \
  -d "outFields=ADDRESS,PID,LIST_GUID&returnGeometry=true&outSR=4326&resultRecordCount=5&f=json"
```
- 返回读法:`geometry.x`=lon、`geometry.y`=lat;`attributes.PID`=LIST 物业 ID(与地块层 PID 对得上);单元类地址形如 `UNIT 1 132 TOLOSA STREET GLENORCHY`,`PID` 可能为 null(个别门牌无 PID,如 243 Tolosa St)。
- 实测状态:✅ 实测通过。`116 TOLOSA STREET GLENORCHY` → PID 5397238.0,x=147.26837358,y=-42.84212759。
- 注意:地址字段是大写、无逗号、无州名;需自行把用户输入标准化后再 LIKE。LIKE 查询对「UNIT 1 132」类写法敏感,先去掉 UNIT/Suite 再试一次。

### 1b 坐标 → 地块(lot/title、面积、tenure、strata)
- 来源:LIST `Public/CadastreParcels/MapServer/0`「Cadastral Parcels」(Land Tasmania / LIST)
  出处:https://services.thelist.tas.gov.au/arcgis/rest/services/Public/CadastreParcels/MapServer/0
- 命令:
```bash
curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/CadastreParcels/MapServer/0/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
  取边界:把 `returnGeometry=false` 换成 `returnGeometry=true&outSR=4326`。
- 返回字段怎么读:
  - `VOLUME`/`FOLIO` = Certificate of Title 卷/页(Volume 42377 Folio 5);`PID`;`LPI`=Local Parcel Identifier;
  - `CAD_TYPE1`=Private Parcel;`TENURE_TY`=权属类型:`Freehold Title`(普通永久业权)/`Horizontal Strata`(单元 strata 地块)/`Body Corporate`(strata 公共产权地块)/Crown 相关等;
  - `STRATA_LEV`:本次实测两类都是 "Not Applicable",**不能用它判断是否 strata,要看 `TENURE_TY`**;
  - `COMP_AREA`=GIS 计算面积 m²;`MEAS_AREA`=登记测量面积 m²;`PROP_ADD`=标准化地址。
- 实测状态:✅ 实测通过
  - 测试地址:VOLUME 42377 / FOLIO 5,PID 5397238,LPI HCG20,Private Parcel,**Freehold Title**,STRATA_LEV Not Applicable,**COMP_AREA 566.105 m² / MEAS_AREA 556 m²**,PROP_ADD "116 TOLOSA ST GLENORCHY TAS 7010"。
  - strata 对照(`UNIT 1 132 TOLOSA STREET`,点查返回 **2 条**):一条 `TENURE_TY=Body Corporate`、FOLIO 0、PID 0(公共产权 1853.9 m²);一条 `TENURE_TY=Horizontal Strata`、PID 2502565、87 m²、PROP_ADD "UNIT 1 132 TOLOSA ST ..."。
- 判读注意:
  1. **点落在 strata 楼上时会返回多层(公共产权 + 各单元)**,skill 里必须取 `TENURE_TY=Horizontal Strata`(或 Vertical)那条做单元,取 `Body Corporate` 那条做公共面积。
  2. 单元面积是 strata 地块的「单元面积」,不是土地份额;土地份额要看 strata plan(LIST Properties & Titles,付费/登录,见 §6)。
  3. TAS 是 freehold 为主;**无 ACT 式 Crown lease 问题**(Crown/授权土地在 `TENURE_TY` 或 LIST「Land Tenure」层 OpenDataWFS/26 里体现,本次未实测)。

### 1c WFS(可选,整批下载用)
- `https://services.thelist.tas.gov.au/arcgis/services/Public/OpenDataWFS/MapServer/WFSServer?service=WFS&request=GetCapabilities`
- 实测状态:✅ GetCapabilities 返回 HTTP 200,WFS 2.0.0(OpenDataWFS 含 LIST Cadastral Parcels/Crown Leases/Land Tenure/Transport Segments 等 54 个图层,层号见服务目录)。未对 WFS 做 GetFeature 点查(REST 已够用)。
- 注意:`Public/CadastreParcels` 自己的 `/WFSServer` 在 `arcgis/services` 路径下返回 400——只有 `Public/OpenDataWFS` 与 `Public/PlanningOnline`(capabilities 含 WMSServer)是对外提供 OGC 的。

---

## 2. 规划分区 zone + overlays(含 heritage)

### 2a Zone(Tasmanian Planning Scheme)
- 来源:LIST `Public/PlanningOnline/MapServer/13`「Tasmanian Planning Scheme Zones」(数据由 Tasmanian Planning Commission 维护;服务描述原文:"Planning scheme mapping developed under the Land Use Planning and Approval Act, including Planning Zones, Planning Overlays and Planning Zone Boundaries maintained by The Tasmanian Planning Commission")
  出处:https://services.thelist.tas.gov.au/arcgis/rest/services/Public/PlanningOnline/MapServer/13
- 命令:
```bash
curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/PlanningOnline/MapServer/13/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 返回字段:`LPS`=Local Provisions Schedule(哪个市);`ZONE_NO`/`ZONE`=分区(8 = General Residential);`ZONE_ABB`=`113.8`(LPS 号.分区号);`LPSDATE`=该 LPS 生效日(毫秒时间戳);`AMEND_REF`;`CREATED_ON`=图层记录创建日。
- 实测状态:✅ 测试地址 → `ZONE = General Residential`,`LPS = Glenorchy Local Provisions Schedule`,`ZONE_ABB 113.8`,`LPSDATE = 1629244800000`(= **2021-08-18**),`NOTES = Alterations of electronic planning map made under s.80O of LUPAA`,`CREATED_ON 2026-03-17`。
- 相关图层(已验证存在):`16` Zone Boundaries;`27/26/25/24` 为「Historical」历史版本;`8` Local Government Areas;`7` Tasmanian Planning Reference。
- **Kingston 一带存疑**:同一服务里还有 `1/3/4`「Kingborough Interim Planning Zones/Overlay」——Kingborough 是否仍用 Interim Scheme 需要用 Kingston 地址同时查 `13` 与 `4`,**未实测**。
- 判读注意:zone 只给分区名,**最小地块/高度/建筑密度/多户住宅规则要去 State Planning Provisions 的 GRZ 条文**(planning.tas.gov.au)。skill 里不要凭分区名推断「可否加盖第二栋」。

### 2b Overlays(Code overlay + General overlay)
- 来源:`PlanningOnline/MapServer/14`「Tasmanian Planning Scheme Code Overlay」(字段 `CODE`、`OV_NAME`、`LPS`)与 `/15`「General Overlay」(字段 `OV_TYPE`、`OV_NAME`:Specific Area Plan / Site-specific Qualifications / Local Area Objectives 等)。
- 命令(两层各查一次):
```bash
for L in 14 15; do
curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/PlanningOnline/MapServer/$L/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"; done
```
- 已验证的 Glenorchy LPS 下 Code overlay 全集(`CODE` → `OV_NAME`,来自 distinct 查询,`LPS_NO=113`):Bushfire-prone Areas Code→Bushfire-prone areas;Coastal Erosion Hazard Code→(Low/Medium/High hazard band, Coastal erosion investigation area);Coastal Inundation Hazard Code→(Low/Medium/High hazard band);Flood-prone Hazard Areas Code→Flood-prone areas;Landslip Hazard Code→(Low / Medium / Medium-active / High landslip hazard band);Local Historical Heritage Code→(Local heritage place / Place or precinct of archaeological potential / Significant trees);Natural Assets Code;Scenic Protection Code;Electricity Transmission Infrastructure Protection Code;Parking and Sustainable Transport Code;Road and Railway Assets Code(Road or railway attenuation area 等);Safeguarding of Airports Code(Airport noise exposure area / obstacle limitation area,在 Clarence、Sorell LPS);Attenuation Code;Potentially Contaminated Land Code(全州 distinct 列表含,Glenorchy 未必有)。
- **全州 Code 种类(layer 14 distinct CODE,实测)**:Attenuation / Bushfire-prone Areas / Coastal Erosion Hazard / Coastal Inundation Hazard / Electricity Transmission Infrastructure Protection / Flood-prone Hazard Areas / Landslip Hazard / Local Historical Heritage / Natural Assets / Parking and Sustainable Transport / Potentially Contaminated Land / Road and Railway Assets / Safeguarding of Airports / Scenic Protection。
- 实测状态:✅ 查询机制通过。
  - 测试地址(116 Tolosa St):`14` 与 `15` **均返回 0 条** = 无任何 overlay(无 flood、landslip、bushfire、heritage、coastal)。
  - 阳性对照 A(147.2400, -42.8350,Glenorchy 山麓):返回 Scenic protection area、Priority vegetation area、**Bushfire-prone areas**(均 LPS 113,LPSDATE 2021-08-18)。
  - 阳性对照 B(Salamanca Place 147.3330, -42.8865):`15` 返回 "Activity Area 2.0 (Sullivans Cove Mixed Use)",Hobart LPS 114(LPSDATE 1761091200000 = 2025-10-22)。
- 判读注意:
  1. **overlay 为「点命中」**:边界地块请改 `geometryType=esriGeometryPolygon` 传地块边界(先 1b 取 geometry)或 buffer(`distance=15&units=esriSRUnit_Meter`),否则地块一角在 overlay 内会漏判。
  2. Code overlay 数量上限 `maxRecordCount=2000`(distinct/按 LPS 批量查时要翻页)。
  3. 不同 LPS 的 `OV_NAME` 措辞略不同,skill 里用 `CODE`(稳定)匹配,别用 `OV_NAME` 全文匹配。

### 2c Heritage(两层)
1. **本地遗产(规划方案内)**:overlay 14 中 `CODE = Local Historical Heritage Code`(见上)。
2. **州遗产登记册 Tasmanian Heritage Register**:`HT/HT_Public/MapServer/0`(Heritage Tasmania)
   出处:https://services.thelist.tas.gov.au/arcgis/rest/services/HT/HT_Public/MapServer/0
```bash
curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/HT/HT_Public/MapServer/0/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
   字段:`THR_ID`、`THR_NAME`、`REG_STATUS`(如 Permanently Registered)、`LOC_ADD`、`TITLE_REF`、`MUNICIPALITY`。
- 实测状态:✅ 测试地址两层均 0 条(非遗产);THR 阳性对照(Salamanca Place 一带 envelope)返回 THR_ID 1943 "Warehouse"、REG_STATUS "Permanently Registered"、TITLE_REF 127919/4。

---

## 3. 洪水

### 3a 规划方案洪水 overlay(法定、首选)
- 即 §2b 的 `CODE = Flood-prone Hazard Areas Code`(`OV_NAME = Flood-prone areas`)。
- 测试地址:✅ 0 条。
- 阳性对照:Glenorchy 北部 (147.22978, -42.77046) 命中该 overlay(经「在 overlay 面内取格点」法验证,overlay 面存在于 LPS 113)。

### 3b SES(State Emergency Service)洪水模型栅格:`Public/SES_FloodMapping/MapServer`
- 出处:https://services.thelist.tas.gov.au/arcgis/rest/services/Public/SES_FloodMapping/MapServer
- 层号(已验证):`10/11` 1% AEP Hazard Riverine/Overland;`12/13` 1% AEP Depth Riverine/Overland;`14/15` Velocity;`16/17` Water Level;`2%`=0–7;`0.5%`=20–27;`30–37` 为 1% AEP + 气候变化。
- 这些是栅格层,**不能 /query,用 /identify**:
```bash
curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/SES_FloodMapping/MapServer/identify" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&sr=4326&layers=visible:10,11,12,13,32,33&tolerance=2&mapExtent={lon_minus},{lat_minus},{lon_plus},{lat_plus}&imageDisplay=600,400,96&returnGeometry=false&f=json"
```
  (`mapExtent` 取点周边 ±0.01°即可,但**必须传**,否则报 400 Invalid or missing input parameters;`layers=all` 也可,返回体很长。)
- 返回读法:`attributes["Pixel Value"]`:**`NoData`=该点无模型淹没值**;数字=水深(m,Depth 层)或 hazard 等级(Hazard 层 `Pixel Value 1` 起)。
- 实测状态:✅ 机制通过。
  - 测试地址:全部图层 `NoData`。
  - 阳性对照 (147.22978, -42.77046):`1 PCT AEP Depth Overland` = **0.043 m**,`... Hazard Overland` = 1,`... Depth Overland [Climate Change]` = **0.048 m**;Riverine 层 NoData。
- 判读注意:
  1. **`NoData` ≠ 无洪水风险**:SES 模型只覆盖已建模的集水区/市,模型外也是 NoData。必须与 3a 的 TPS flood overlay、以及市政府洪水图合并判读,且在报告里写「模型覆盖未确认」。
  2. 栅格 identify 对 `tolerance` 敏感,点落在建筑物/道路上可能是 NoData(地面建模剔除)。
  3. 另有 `Public/SES_FloodMapping_Calibration1/2`(历史洪水事件校准,如 2016 年 6 月、2018 年 5 月、1929 年以来事件)可作「历史淹没」对照,未实测。

### 3c TasWater Flood Inundation Summary(`Public/Infrastructure/MapServer/6`)
- 测试地址点查返回 **1 条**:`WATERCOURS = Humphreys Rivulet`,`DAM = Tolossa / Limekiln / Knights Creek`,`FILE_REFER = FSW10/863-003 ...`。图层说明仅一句:"The Flood Inundation Summary has been supplied by TasWater. For more information, contact TasWater on 136 992"。
- **存疑**:字段含 `DAM`,疑似「水坝失事淹没范围」而非常规 1% 洪水;语义**未核实**,skill 里先作「提示项:需向 TasWater 确认」,不要直接当作洪水风险结论。

### 3d 海岸/风暴潮(TAS 的「storm surge」对应物)
- 见 §5「海岸侵蚀与淹没」。

---

## 4. 山火(bushfire-prone areas)

- 法定:§2b `CODE = Bushfire-prone Areas Code`(`OV_NAME = Bushfire-prone areas`)。
- 补充:`Public/EmergencyManagementPublic/MapServer` 含 `62` TFS Bushfire Impact Area、`65-68` TFS BRMP(Bushfire Risk Management Plan)Human Settlement/Natural/Other/Production Forests、`1/2/13/14` Fire History。
  ```bash
  curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/EmergencyManagementPublic/MapServer/65/query" \
    -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
  ```
- 实测状态:✅ 测试地址:Bushfire-prone overlay 0 条;TFS BRMP Human Settlement(65)0 条。阳性对照 (147.2400,-42.8350):命中 Bushfire-prone areas(§2b)。
- 判读注意:overlay 命中的法定后果(是否触发 BAL 评估/bushfire hazard management plan)**未实测核对**,须查 Tasmanian Planning Scheme 的 Bushfire-prone Areas Code 条文;skill 里只输出「命中/未命中」+ 指向条文,不做 BAL 等级判断。

---

## 5. 滑坡 / 酸性硫酸盐土 / 海岸侵蚀与淹没 / 其它

### 5a 滑坡(Landslip,TAS 重点)
- 法定:§2b `CODE = Landslip Hazard Code`,`OV_NAME` ∈ {Low, Medium, Medium-active, High landslip hazard band}(全部在 Glenorchy LPS 下实测存在)。
- 原始地质调查图:`Public/GeologicalAndSoils/MapServer/23`「Landslide Planning Map - Hazard Bands」与 `/24`「Components」(Mineral Resources Tasmania)
```bash
curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/GeologicalAndSoils/MapServer/23/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
  字段:`HAZARD_BAND_1`(Low/Medium/High)、`COMPONENT`、`NAME`(地名)、`NAME_1`(council)、`HAZARD_EXPOSURE`(文字说明)、`VERSION`、`VERSION_DATE`、`FURTHER_INFORMATION`。
- 实测状态:✅ 测试地址 `23`/`24` 与 overlay 均 0 条(平坦地,未入图)。阳性对照(envelope 147.23–147.28, -42.85– -42.80):`HAZARD_BAND_1="Low"`,`COMPONENT="Debris flow susceptibility Mountain runout 22-12 Q4a"`,`NAME="Berriedale"`,`NAME_1="Glenorchy City Council"`,`VERSION="Version 2"`,`VERSION_DATE="19 August 2013"`,`HAZARD_EXPOSURE="This area has no known active landslides, however it has been identified as being susceptible to landslide by Mineral Resources Tasmania (MRT)."`
- 判读注意:
  1. **TAS 的 Landslip hazard band 才是规划法定口径**;`GeologicalAndSoils/23` 是同一来源的调查版(版本日期 2013),优先看 overlay(跟随 LPS 更新)。
  2. Medium-active / High band 在 TPS 里有额外 development standard(甚至需地质师报告),这是 TAS 估值与可开发性的实质因素。**但条文要求没有实测引用**,skill 里写「命中 → 查 C15.0 Landslip Hazard Code 条文」,不要自己概述要求。
  3. 没有逐点「坡度」数值服务;`Public/TopographyAndRelief`、LiDAR index 可补,未实测。

### 5b 酸性硫酸盐土(ASS)
- 图层:`GeologicalAndSoils/MapServer/20`(Coastal ASS 0–20 m AHD)、`/21`(Inland ASS >20 m AHD)、`/22`(Marine Subaqueous-Intertidal ASS)、`/0`(ASS Sites)。`/20` 字段含 `ASS_PROBAB`(概率分类)、`ELEVATIONZ`、`GEOLOGY_*`、`SOIL_*`、`HECTARES`。
```bash
curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/GeologicalAndSoils/MapServer/20/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=ASS_PROBAB,ELEVATIONZ,DATASET_NA,HECTARES&returnGeometry=false&f=json"
```
- 实测状态:✅ 查询通过,测试地址 20/21/22/0 均 0 条;**阳性对照未找到**(Montrose 三个试点均 0)。说明:`/20` 描述为 NHT 资助 NRM Cradle Coast 项目(覆盖面偏北部/沿海),Hobart 南部覆盖度未确认——**不要把 0 条解读为无 ASS**。
- 规划口径替代:TPS 里 ASS 通过 Specific Area Plan/local 条款(如 Glenorchy LPS 的「Beedhams Bay Potential Acid Sulfate Soils Specific Area Plan」,在 overlay 15 distinct 列表中)和 Potentially Contaminated Land Code 体现。

### 5c 海岸侵蚀与淹没(含 storm surge/sea level rise 等价物)
- 法定:§2b `Coastal Erosion Hazard Code`(Low/Medium/High bands + investigation area)、`Coastal Inundation Hazard Code`(Low/Medium/High bands)。
- 原始调查图:`Public/MarineAndCoastal/MapServer/81`(Coastal Erosion Hazard Bands 20161201)、`/82`(Erosion Component)、`/83`(Coastal Inundation Hazard Bands 20161201,字段 `HAZARD_BAND`、`HEIGHT_HIGH/MEDIUM/LOW`、`HAT`、`LOCAL_STORM_SURGE`、`WAVE_SETUP`、`WAVE_RUNUP`);`Public/ClimateChange/MapServer/44–47`(1% AEP storm tide 2010/2050/2100,sea level rise 20161201)。
- 实测状态:✅ 测试地址 `ClimateChange` 44/45/46/47 均 0 条、overlay 均无(内陆约 1.5 km 外)。阳性对照:Clarence LPS(147.2950,-42.8030)返回 Bushfire/Priority vegetation/Road or railway attenuation area,**未取到 coastal overlay 命中**(海岸命中点未在本次实测中找到)——coastal 机制仅「图层存在、测试地址未命中」。

### 5d 其它
- 电力输电走廊/变电站:`Electricity Transmission Infrastructure Protection Code`(overlay);**测试地址 0 条**。
- 污染地:`Potentially Contaminated Land Code`(overlay 14 distinct 中存在)。
- 供排水:`Public/Infrastructure/MapServer/0`(TasWater Sewer Serviced Land)、`/1`(Water Serviced Land)——可判断是否接市政水/污水,测试地址**未查**。

---

## 6. 官方估价(逐地块)

- 目标:Valuer-General 的 Land value / Capital value / Assessed Annual Value(AAV)。
- 实测状态:**❌ 无免费公开的逐地块估价接口(测试已穷尽三条路)**:
  1. LIST 全部 `Public/*`、`HT`、`NCH` MapServer 图层名扫描(valu/valuation 关键词)——0 个估值图层;`CadastreParcels/0` 字段表无估值字段。
  2. LIST「Properties and Titles」`https://www.thelist.tas.gov.au/app/content/property/property-search` 实测打开为**登录页**(需 LIST 账户);LIST 帮助 PDF(`.../resources/properties.pdf`)目录显示为产权文档/Property Sales/Torrens 扫描件等购物车式产品;WebSearch 摘要提到 "Premium Property Reports ... For a small charge, property sales information is available from www.thelist.tas.gov.au"(来源页:dpac.tas.gov.au / hobartcity 评估手册),即**收费**。
  3. NRE Tas Valuer-General 页 https://nre.tas.gov.au/land-site/Pages/Statutory-Valuations---Revaluations-and-Supplementary-Valuations.aspx 只给电话 03 6165 4444 / ovg@nre.tas.gov.au,无公开查询入口。
- 兜底(人工):物业 rates notice(市政府);Valuation Roll 查询——联系 OVG。skill 里只能输出「估价需人工/付费,入口 https://www.thelist.tas.gov.au (Properties and Titles)」。
- 估价周期(官方 nre.tas.gov.au 摘要):全 LGA 每 6 年重估一次,重大变化时补充估价(来源=WebSearch 摘要,未直接引原文)。

---

## 7. DA / 开发活动公开接口

- **州级统一的 DA 公开接口:❌ 未找到**(TAS DA 在各 council 系统)。
- 已尝试:(1) LIST/ArcGIS Hub 搜索 Glenorchy/Hobart development applications(无 TAS 官方 DA 图层;Hobart 市有 open data hub `https://data-1-hobartcc.opendata.arcgis.com`,仅见规划方案/道路等,**DA 层未找到**);(2) Glenorchy City Council 网站为 planning decisions 列表与到访查阅,WebSearch 摘要未见 API;(3) 第三方 morph.io 爬虫存在(`Bigben83/glenorchy_council_TAS_development_applications`)——**非官方,不采用**。
- 结论:⚠️ 需浏览器人工看 council DA 页(Glenorchy:https://www.gcc.tas.gov.au/planning-and-development.aspx;Hobart:hobartcity.com.au;Kingborough:kingborough.tas.gov.au)。
- 补充:`CadastreAndAdministrativeV2`/OpenDataWFS 中没有 DA;`TasmaniaPlanningCommission` 的 planning notices 在 planning.tas.gov.au(未实测)。

---

## 8. 道路车流量、铁路线、机场 ANEF

### 8a 道路车流量(AADT)
- ❌ 未找到免费逐路段 AADT 开放数据:LIST 图层名扫描(traffic/aadt)=0;data.gov.au 上 Tas State Growth 数据集仅含 crash data、Heavy Vehicle Routes、Low Bridge Clearances、Load Limited Bridges、Speed Limits(WebSearch 摘要);州议会文件提到 "Key Arterials Traffic Data Catalogue" PDF(非开放数据)。
- 兜底:State Growth 空间服务组邮箱(摘要提供):SpatialServicesGroup@stategrowth.tas.gov.au;或 transport.tas.gov.au 的 traffic count 页(未实测)。
- 道路等级可用 `OpenDataWFS/MapServer/42`「LIST Transport Segments」(字段 `TRAN_CLASS` 如 Sub Arterial Road/Access Road、`SURFACE_TY`、`AUTHORITY`)
  ```bash
  curl -s -G "https://services.thelist.tas.gov.au/arcgis/rest/services/Public/OpenDataWFS/MapServer/42/query" \
    -d "geometry={lon_w},{lat_s},{lon_e},{lat_n}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=TRAN_CLASS,SURFACE_TY,AUTHORITY,PRI_NAME,TRANS_TYPE&returnGeometry=false&f=json"
  ```
  ✅ 实测:测试地址周边 envelope 返回 Sub Arterial Road(Council)等;注意 `PRI_NAME`(路名)在样本里为 null,路名要用 `Named Features`/`SearchService` 补。

### 8b 铁路
- 图层:`Public/TopographyAndRelief/MapServer/26`「Railways」、`/32` Railway Distance Markers、`/56` Railway Crossings;规划口径 overlay:`Road and Railway Assets Code` → `Road or railway attenuation area` / `Future major railway`。
- 实测:✅ 查询通过;测试地址 ±1 km envelope Railways 返回 0(**本次未做阳性对照,不保证 Glenorchy 区间内无铁路**——Hobart 北郊 Brighton 线存在,请用 envelope 扩大到 1–2 km 复查)。

### 8c 机场 / ANEF
- TAS 规划方案里没有 ANEF 等值线本身,用 `Safeguarding of Airports Code` overlay(`Airport noise exposure area`、`Airport obstacle limitation area`)。实测:该 OV_NAME 在 Clarence LPS 与 Sorell LPS 存在(extent x 143.85–147.61, y -42.86 – -39.86,覆盖 Hobart、Launceston 等机场);测试地址 0 条。
- ⚠️ 官方 ANEF 图是各机场 Master Plan/Airservices PDF(Hobart Airport),**不是接口**。skill 里的做法=overlay 命中则提示「在机场噪音暴露区」并指向机场 Master Plan。

---

## 9. 政策红利(与住宅增值潜力相关的现行政策)

只认官方原文 + 生效日期。**本辖区实测结果:⚠️ 没有取得可引用的、已生效的官方原文**。

- 已核实的官方线索(经 WebSearch 摘要读到,**原页 curl 被 Cloudflare 403,未能取原文,故不引整句**):
  - Tasmanian State Planning Office「Improving residential standards in Tasmania」项目:拟改 General Residential / Inner Residential / Low Density Residential 区住宅标准;**Final Report 发布于 2024 年 10 月**(PDF:https://stateplanning.tas.gov.au/__data/assets/pdf_file/0009/564480/Improving-Residential-Standards-in-Tasmania-Final-Report-Oct-2024.pdf);**Recommendations Report 公布日 2025-03-03**(据 stateplanning.tas.gov.au 新闻摘要);**Medium Density Design Guidelines 2025 年 5 月发布**(同站新闻摘要)。摘要称建议将用于起草 SPP(State Planning Provisions)修订,修订需公示并经 Tasmanian Planning Commission 评估。
  - **状态判断:建议已发布,SPP 修订尚未见生效日**——skill 里不得写成「TAS 已放开 dual occupancy」。
- 人工入口:https://www.stateplanning.tas.gov.au (State Planning Office);https://www.planning.tas.gov.au (Tasmanian Planning Commission,SPP amendment 状态)。

---

## 测试地址实测结果汇总表(116 Tolosa Street, Glenorchy TAS 7010)

| 检查项 | 数据源 | 状态 | 测试地址返回值 |
|---|---|---|---|
| 地址→坐标 | LIST SearchService/7 | ✅ | 147.26837358, -42.84212759;PID 5397238 |
| 地块 | LIST CadastreParcels/0 | ✅ | Vol 42377 Folio 5;Freehold Title;556 m²(GIS 566.1) |
| strata 判断 | 同上 TENURE_TY | ✅ | 本址非 strata;对照 Unit 1/132 Tolosa=Horizontal Strata+Body Corporate |
| 分区 | PlanningOnline/13 | ✅ | General Residential(Glenorchy LPS,LPS 生效 2021-08-18) |
| Overlays(Code+General) | PlanningOnline/14,15 | ✅ | 无 |
| Heritage(本地+THR) | overlay 14 + HT/0 | ✅ | 无 |
| 洪水(TPS overlay) | overlay 14 | ✅ | 无 |
| 洪水(SES 栅格) | SES_FloodMapping identify | ✅(机制)/⚠️(覆盖) | NoData(不等于无风险) |
| TasWater Flood Inundation Summary | Infrastructure/6 | ⚠️ | 命中 Humphreys Rivulet / Tolossa-Limekiln-Knights Creek(语义存疑) |
| 山火 | overlay 14 + EMP/65 | ✅ | 未命中 |
| 滑坡 | overlay 14 + GeoSoils/23,24 | ✅ | 未命中 |
| ASS | GeoSoils/20,21,22,0 | ⚠️(覆盖度) | 未命中 |
| 海岸侵蚀/淹没/风暴潮 | overlay + ClimateChange/44–47 | ✅(机制) | 未命中 |
| 官方估价 | — | ❌ | 无免费源;LIST P&T 需登录/付费 |
| DA | council | ⚠️ | 需人工看 Glenorchy CC |
| 道路车流量 | — | ❌ | 未找到 AADT |
| 道路等级 | OpenDataWFS/42 | ✅ | 周边 Sub Arterial(Council) |
| 铁路 | TopographyAndRelief/26 | ✅(机制) | ±1 km 0 条(无阳性对照) |
| 机场 ANEF | overlay(Safeguarding of Airports) | ⚠️ | 无命中;ANEF 图需机场 Master Plan |
| 政策红利 | stateplanning.tas.gov.au | ⚠️ | 建议已出,修订未见生效 |

## 未解决 / 存疑清单(TAS)

1. **官方估价**:无免费逐地块源;LIST Properties and Titles 价格/内容(估价是否含在 Premium Property Report)只来自搜索摘要,**未登录验证**。
2. **TasWater Flood Inundation Summary**(Infrastructure/6)含义未核实(疑坝溃淹没范围);需联系 TasWater 或读元数据。
3. **Kingston(Kingborough)** 仍有 Interim Planning Scheme 图层(PlanningOnline 1/3/4),是否已迁入 TPS 未实测;skill 对 Kingborough 地址需同时查 13 与 4。
4. **ASS** 覆盖度:测试点与对照点均未命中,不能确认 Hobart 南部有无覆盖。
5. **海岸 overlay** 阳性命中未取到(仅验证 overlay 类别存在);Coastal Inundation/Erosion 的命中点需用沿海地址复测。
6. **铁路**无阳性对照;envelope 半径需放大。
7. **SES 洪水栅格**:模型覆盖范围未取得(NoData 含义二义)。
8. **车流量**:州级 AADT 开放数据未找到;可能存在于 State Growth 内部/PDF。
9. **政策**:stateplanning.tas.gov.au、planning.tas.gov.au 对 curl 返回 403(Cloudflare),只能经 WebSearch 摘要或浏览器取原文;SPP 修订生效日未取得。
10. WFS 只验证了 GetCapabilities;未测 GetFeature 与 CRS 输出。
11. LIST 服务是匿名公开,但**未查到官方速率限制/使用条款**;批量化前请读 LIST Terms and Conditions。
