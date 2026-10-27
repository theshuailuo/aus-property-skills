# Queensland (QLD) 州适配说明 — 澳洲住宅物业尽调 skill

实测日期:2026-10-03(所有「实测」均在此日期用 curl / Python urllib 直接打接口,拿到真实返回)。
只用官方、免费、公开源。未使用 HtAG / CoreLogic / Landchecker 等付费源。
图层号、字段名、URL 均为实测;未实测处明确标「未实测」。

## 0. 总览与总流程(QLD 与 NSW 最大差别)

QLD **没有全州统一的规划分区/overlay 图层**,必须:
1. 州级 QLocator 地址→坐标;州级 DCDB 取 lot/plan → 判定 council(`shire_name`);
2. 按 council 分流到该 council 的公开数据(Brisbane 最强,一张「逐地块 flags 表」就能拿到全部 overlay);
3. 州级图层只补:rail、AADT(只到 2020)、abandoned mines、QFAO(SEQ 市区基本无覆盖)、州级 LGA 属性。

通用参数:`{lon} {lat}` = WGS84 经纬度(QLocator 返回的 x=lon, y=lat);`{lotplan}` = 如 `112RP146054`。
所有 ArcGIS 点查通用模板(inSR=4326):

```
curl -s -G "{LAYER_URL}/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
「附近 N 米」把 `-d` 追加 `distance=500&units=esriSRUnit_Meter`(点到线/面的邻近检索)。
辅助脚本(本次会话用,放在 `scratchpad\qld\`):`geo.py`(地址→坐标)、`qq.py`(点查并紧凑打印)、`near.py`(邻近+算最近距离)、`lp.py`(BCC lotplan 全 flags+洪水指标并解码)。

Windows 注意:Python 打印中文/特殊字符需 `PYTHONIOENCODING=utf-8`;Git Bash 的 `/tmp` 与 Windows Python 的路径不通,临时文件用 Python 直接写 `scratchpad`。

### 测试地址
| 代号 | 地址 | 坐标 (lon, lat) | council |
|---|---|---|---|
| A(主测) | 56 Denham St, Bracken Ridge QLD 4017 | 153.042138, -27.327258 | Brisbane City |
| B1 | 20 Steven Court, Narangba QLD 4504 | 152.955423, -27.199764 | Moreton Bay |
| B2 | 30 Brisbane Road, Redbank QLD 4301 | 152.865045, -27.602217 | Ipswich |
| B3 | 25 Station Road, Loganlea QLD 4131 | 153.125298, -27.66951 | Logan |
| B4(仅图层摸底) | 40 Poinsettia Avenue, Runaway Bay | 153.401688, -27.902817 | Gold Coast |
| B5(仅图层摸底) | 10 Beerburrum Street, Dicky Beach | 153.1378035, -26.783631 | Sunshine Coast |

---

## 1. 地址 → 坐标 → 地块 / lot-plan / 面积 / strata 判定

### 1.1 地址→坐标(QLocator)
- 来源:Queensland Government spatial-gis `Location/QldLocator` GeocodeServer(QSpatial)。
- 命令:
```
curl -s -G "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Location/QldLocator/GeocodeServer/findAddressCandidates" \
  --data-urlencode "SingleLine={street address, suburb QLD postcode}" -d "maxLocations=1&outSR=4326&outFields=*&f=json"
```
- 读法:`candidates[0].location.x`=lon,`.y`=lat;`score`≥95 且 `Addr_type=PointAddress` 才可信。**务必带 `outFields=*`**,否则 attributes 为空(实测踩坑)。`Location/QldCompositeLocator` 也可用(返回无 attributes)。
- 实测 ✅:A → x=153.042138,y=-27.327258,score 98.62,PointAddress。B1/B2/B3 均 98.57 PointAddress。
- 注意:同名街在州内会被匹配到别的城镇(实测 "15 Dunlop Street, Caboolture" 被匹配到 Kelso 146.7E,score 81.9)—**score<90 或经度不在 SEQ 就当失败**。

### 1.2 坐标→地块(DCDB)
- 来源:`PlanningCadastre/LandParcelPropertyFramework` MapServer(QSpatial,官方 DCDB)。图层(实测):0 Addresses;4 Cadastral parcels(全部);8 Base Parcels Only;10 Strata Parcels Only;50 Properties(命名物业,非估价)。
- 命令:
```
curl -s -G "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/PlanningCadastre/LandParcelPropertyFramework/MapServer/4/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=lot,plan,lotplan,tenure,lot_area,parcel_typ,cover_typ,locality,shire_name&returnGeometry=false&f=json"
# 要边界:改 returnGeometry=true&outSR=4326
# 地址表(带 unit→lot 对应):.../MapServer/0/query  同参数 + distance=10&units=esriSRUnit_Meter
```
- 读法:`lotplan`=lot+plan;`lot_area`=m²(DCDB 面积,非测量面积);`tenure`;`cover_typ`=Base/Strata;`shire_name`=council(决定后续分流);`st_area(shape)` 是度单位,忽略。
- 实测 ✅ A:`112RP146054`,698 m²,Freehold,cover_typ=Base,Lot Type Parcel,Bracken Ridge,Brisbane City。地址表:`56 Denham Street Bracken Ridge QLD` → `112RP146054`。
- 实测 ✅ B1:`21SP191127` 500 m²;B2:`1RP127017` 756 m² Ipswich City;B3:`6RP110606` 809 m² Logan City。

### 1.3 strata / community title 判定
- plan 前缀含义(QLD):**RP**=Registered Plan(普通地块);**SP**=Survey Plan(多数为标准 subdivision,也用于社区产权方案 CTS);**BUP**=Building Units Plan(旧 unit 楼,1997 前);**GTP**=Group Titles Plan(旧 group title);**CP**=Crown Plan。判定别只看前缀,看 `cover_typ`。
- 实测规则 ✅(Bracken Ridge `SP166489`,点 153.024088,-27.326361):同一点查图层 4 返回 2 条 —— `1SP166489`(cover_typ=Base,960 m²,地址 12 Gawler Cres)+ `BSP166489`(cover_typ=Strata,274 m²,**字母 lot=公共财产/楼体格式地块**)。图层 10 只返回 Strata 那条。个别单元 lot(如 `8SP166489`)没有独立多边形,但在地址表(图层 0)里有 `address`→`lotplan` 对应。
- 判读:点查命中 ≥2 条且含 `cover_typ=Strata` → strata/CTS;Brisbane 内 `plan LIKE 'BUP%'` 实测 172 条、`SP%` 1,304 条(locality='Brisbane City')。A 的 `RP146054` + Base + 单条 → **非 strata,Torrens 独立地块**。
- GTP:locality 过滤下 Brisbane City/Redcliffe 查得 0 条(未做全州核实),**未实测**。
- 估价与产权:QLD 不单独给 strata 单元估价,见第 6 节。

---

## 2. 规划分区 zone + overlays(按 council)

### 2.1 Brisbane City Council — Brisbane City Plan 2014(✅ 最强)
- 来源:BCC Open Data(ArcGIS Online 组织 `services2.arcgis.com/dEKgZETqwmDAh1rP`,owner=brisbaneopendata);门户 https://data.brisbane.qld.gov.au (Huwise/Opendatasoft API v2.1 可用)。
- 版本:Zoning_opendata/Flags 的 `dataLastEditDate`=2026-09-17/29;官方页面称 City Plan Amendment **v37.00/2026** 于 2026-09-18 生效(见第 9 节),数据日期与之吻合,但**图层本身未标版本号**(未实测到 v37 字样)。旧版以 `s_cp2014_vNN_YYYY_*_superseded` 命名,别误用。
- **推荐主法:一次按 lotplan 取全部 flags(zone/overlay/neighbourhood plan/LGIP)**
```
curl -s -G "https://services2.arcgis.com/dEKgZETqwmDAh1rP/arcgis/rest/services/City_Plan_2014_Property_Parcel_Flags/FeatureServer/0/query" \
  --data-urlencode "where=LOTPLAN='{lotplan}'" -d "outFields=*&returnGeometry=false&f=json"
# flag 解码表(783 行):
curl -s -G ".../City_Plan_2014_Property_Parcel_Flags_reference/FeatureServer/0/query" -d "where=1=1&outFields=*&returnGeometry=false&resultRecordCount=1000&f=json"
```
  字段 `CATEGORY`:Z=zone,O=overlay,NP=neighbourhood plan,LGIP=基建规划,OP=其他,Grid。查不到 lotplan(如新批地块)→ 退回下面的空间点查。
- 备用(空间点查,同 org):`Zoning_opendata/FeatureServer/0`(字段 `LVL1_ZONE`、`LVL2_ZONE`、`ZONE_CODE`、`NP`、`NP_PREC`、`ZONE_PREC`);`Dwelling_house_character_overlay`;`City_Plan_2014_PotentialAndActual_acid_sulfate_soils_overlay`;`Neighbourhood_Plan_boundaries`;`Landslide_overlay`;`Bushfire_overlay`;`Flood_overlay_Brisbane_River_flood_planning_area` / `Flood_overlay_Creek_waterway_flood_planning_area` / `Flood_overlay_Overland_flow`;`Transport_noise_corridor_overlay`(点查 A 无命中);ANEF 见第 8 节。统一用 `{ORG}/{service}/FeatureServer/0/query` 点查模板。
- 实测 ✅ A(56 Denham St,lotplan `112RP146054`):
  - Zone:**LDR**(`LVL1_ZONE`=General residential,`LVL2_ZONE`=Low density residential;点查与 flags 一致)。
  - NP:**Bracken Ridge and district neighbourhood plan**(`NP_PREC` 空 → 无具体 precinct)。
  - Overlay flags:**DHO 住宅特色(Dwelling house character)**、AEO(机场环境)+BSZ_D13(鸟蝠撞击区 8-13km)+OLS_HLS+OLS_PANS、BNO、CIO/INF_MPA、CPN-LTIP、**PAS / PAS_A20 / PAS_ASZ**(酸性硫酸盐,>5m<20m AHD)、RHO、SHO;LGIP:PIA、PCF53;OP:SIA(雨水网络)。**无 FO(洪水)、无 BO(山火)、无 LO(滑坡)、无 TNC(噪音走廊)flag。**
  - 点查交叉验证:Dwelling_house_character 命中(CAT=CHA_DHC);ASS 命中;Flood/Landslide/Bushfire/Transport_noise 均 0 条。
- 判读注意:
  - **DHO 在 LDR 上 = 老房保护/拆建限制**,直接影响开发潜力(拆除、分割、新建 secondary 需另查 City Plan 对应 code)。flag 解码为 "Dwelling house character overlay"。
  - 地块 flag 来自 BCC 地块匹配,**新分地块 lotplan 可能缺行**;以空间点查补。
  - `PCF53` 等 LGIP 码在 reference 表中解不出(显示 `?`,实测),不影响尽调结论;`Grid`=BCC 网格号。
  - LDR/LMR/MDR 等 Brisbane zone 代码解码在 reference 表(CATEGORY=Z):如 LDR=Low Density Residential、LMR1=2 storey mix、LMR2=3 or 4 storey mix、MDR、CR1/CR2(Character/Infill housing)、HDR1/2 等。

### 2.2 Moreton Bay Regional Council(✅,Open Data FeatureServer)
- 来源:AGOL org `services-ap1.arcgis.com/152ojN3Ts9H3cdtl`(owner=moretonbaygis);页面 https://www.moretonbay.qld.gov.au/Services/Building-Development/Planning-Schemes/MBRC/Info-Sheets/Mapping-Datasets。
- Zone(带 lotplan,逐地块):
```
curl -s -G "https://services-ap1.arcgis.com/152ojN3Ts9H3cdtl/arcgis/rest/services/ZM_Zones_WebMercator_OpenData/FeatureServer/0/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
  字段:`LVL1_ZONE`、`ZONE_PREC`(precinct)、`LP`/`LP_PREC`(local plan)、`LOT_PLAN`、`Prev_Zone`、`LanduseRates`、`Address`。
- Overlay 同 org(均为 `{ORG}/{name}/FeatureServer/0`,点查模板):`OM_Flood_Hazard_WebMercator_OpenData`、`OM_Overland_Flow_Path_WebMercator_OpenData`、`OM_Coastal_Hazard_Storm_Tide_WebMercator_OpenData`、`MBRC_PlanningScheme_OM_BushfireHazard`、`MBRC_PlanningScheme_LandslideHazardOverlay`、`MBRC_PlanningScheme_OM_AcidSulfateSoils`、`MBRC_PlanningScheme_TransportNoiseOverlay`、`OM_Road_Hierarchy_WebMercator_OpenData`、`MBRC_PlanningScheme_ExtractiveResources_Overlay`、`MBRC_PlanningScheme_OM_WalkingDistance_TrainStation`、`MBRC_PlanningScheme_ZM_LocalPlanBoundary`。
- 实测 ✅ B1(20 Steven Court Narangba,`21SP191127`):Zone=**General residential**,precinct=**Urban neighbourhood**,Prev_Zone=Residential B,LanduseRates=Single Unit Dwelling,Division 11;`WDTS800`=**Narangba 火车站 800m 步行圈内**(命中);Flood hazard / Overland flow / Storm tide / Bushfire / Landslide / ASS / Transport noise / Road hierarchy / Extractive 均 0 条;Local plan boundary 0 条。
- 附带实测:42 Anzac Ave Redcliffe(`589RP30401`)Zone=Centre,precinct=Redcliffe seaside village,LP=Redcliffe Kippa-Ring。
- 注意:Narangba 的 flood/bushfire 等为「0 命中」,**本次未对 MB 洪水层做正例对照**(只确认了图层有数据:Flood Hazard 属性 `FHA_FPA` 等);用于结论前建议对一个已知洪泛 lot 抽查。MB 另有 council 自建服务 `gis-cl6.moretonbay.qld.gov.au/arcgis/rest/services/PlanningMoreton/...`(AGOL 条目列出,**未实测**)。

### 2.3 Logan City Council — Logan Planning Scheme(✅,council 自有 ArcGIS Server)
- 来源:`https://arcgis.lcc.wspdigital.com/server/rest/services/LoganHub/`(版本化服务)。当前实测可用最新为 `Logan_Planning_Scheme_v9_2_TLPI_No_1_2024_20250527`(MapServer)。另有 `Logan_DRAFT_Planning_Scheme_20250821` / `Logan_Base_Data_DRAFT_20250821`(草案,**未实测**,生效状态须到 Logan 官网核实)。每次使用前先列 `LoganHub` 目录找最新版本。
- 图层号(实测):368=ZM-01.00 Zone map;367=ZM-02.00 Precinct map;3=ASS(>5m<=20m 等);21=Bushfire hazard risk area;31=Flood assessment area;39=Flood risk areas;50=≥12% slope;74=Transport noise corridor – State-controlled road(mandatory);75=Railway noise;129/130=Local plan boundary/Precinct area。命令:
```
curl -s -G "https://arcgis.lcc.wspdigital.com/server/rest/services/LoganHub/Logan_Planning_Scheme_v9_2_TLPI_No_1_2024_20250527/MapServer/368/query" \
  -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json"
```
- 实测 ✅ B3(25 Station Rd Loganlea,`6RP110606`):Zone=**Low Density Residential**,precinct=**Small Lot(SL)**;ASS=`PAS_A20`(>5m ≤20m AHD);Flood assessment area=命中("Flood Assessment Area");Flood risk areas=命中("**Low Flood Risk Area**");Transport noise corridor=命中(`TRA_NC1`,"State - Category 1 - Roads");Bushfire 0 条;Slope 0 条;Railway noise 0 条。
- 注意:该服务偶发超时(WinError 10060),**重试一次再判失败**;图层 ID 随版本变,不要硬编码,先 `...MapServer?f=json` 读。Property Report 服务(`Logan_Property_Report_v9_2_...FeatureServer`)存在,字段/用法**未实测**。

### 2.4 Gold Coast — City Plan Version 13(✅ 图层摸底+点查)
- 来源:AGOL `services-ap1.arcgis.com/lnVW0dLI3fvST2hd/arcgis/rest/services/City_Plan_Version_13_Open_Data/FeatureServer`(owner=CoGC_Admin,City of Gold Coast)。
- 图层(实测):4 Zone;12 Land ≤5m AHD(ASS);13 ≤20m AHD;35 Bushfire hazard area;43 Dwelling house overlay area;81 Flood assessment required;94 Airport noise exposure area;95 Landslide hazard;101 Minimum lot size。
- 实测 ✅ B4(40 Poinsettia Av Runaway Bay):Zone=**Medium density residential**,Building_height="2 (9m)";`PAS_A05`(≤5m AHD);`FHA_FAR` Flood assessment required=命中;Dwelling house overlay area=命中;bushfire/ANEF/landslide/minimum lot size=0 条。版本更新频繁(11→12→13),使用前检索最新 "City Plan Version NN Open Data"。

### 2.5 Sunshine Coast — Sunshine Coast Planning Scheme 2014(✅)
- 来源:AGOL `services-ap1.arcgis.com/YQyt7djuXN7rQyg4/arcgis/rest/services/`:`PlanningScheme_Zoning_SCC/FeatureServer`(图层 5 = Zones,字段 `LABEL`)、`PlanningScheme_SunshineCoast_Overlays_SCC_OpenData/FeatureServer`(0=ASS;32/34=Bushfire High/Medium;46=Flooding and Inundation;58=Landslide hazard;59=Steep land;12/18=ANEF)。
- 实测 ✅ B5(10 Beerburrum St Dicky Beach):Zone=**Tourist Accommodation Zone**;ASS=Area 2(>5m <20m);Flood/Landslide/Bushfire=0 条。
- 注意:Zoning 服务点查用图层 5,不是 0(图层 0 不存在,`Invalid URL`)。

### 2.6 Ipswich(⚠️ 开放数据过期 → 必须浏览器)
- **现行规划:Ipswich City Plan 2025,2025-05-29 council 通过,2025-07-01 生效**(官方页面原文:"The new planning scheme was adopted by Council on 29 May 2025" / "took effect on 1 July 2025";页面 https://www.ipswich.qld.gov.au/Services/Planning-and-Building/Planning/Planning-in-Ipswich)。
- 官方查询入口(浏览器):https://ipswich.isoplan.com.au/eplan(页面称显示 zoning 和 overlays)。**脚本访问返回 403**(实测:eplan 及 `/arcgis|/server|/eplan` rest 路径均 403)。
- 开放数据陷阱:data.gov.au 上 Ipswich City Council 发布的 WFS(如 `https://data.gov.au/geoserver/ipswich-plnning-scheme-zones/wfs`)标题全是 **「SUPERSEDED 2006 – Ipswich Planning Scheme」**,Zones 要素 `DATE_PUBLI`=2019-08-02。AGOL 上 Ipswich 相关(`ICC_*_geojson` 等)为第三方转存。**这些不得用于现行分区结论**,只可作历史参考/地下采矿 buffer 线索。
- 实测(过期数据,仅示范 WFS 用法):WFS 1.0.0 + `bbox=...,EPSG:4326` 可用(CQL INTERSECTS 在该 GeoServer 上失效,3 种写法均返回 0,**实测踩坑**):
```
curl -s -G "https://data.gov.au/geoserver/ipswich-planning-scheme-overlay-ov03-mining-buffer/wfs" \
  -d "service=WFS&version=1.0.0&request=GetFeature&typeName=ckan_03baae2d_d64d_4c6b_b8d4_9750f571c055&outputFormat=json&bbox={lon-0.0001},{lat-0.0001},{lon+0.0001},{lat+0.0001},EPSG:4326"
```
  B2(30 Brisbane Rd Redbank)→ `OV3 Mining Constrained Area`(`CA`,"Mining Influence Constrained Areas");Zones 返回 3 条相交(含 `CHM` Character Housing Mixed Density 等,**是 2006 版,仅示范**)。其余 OV 图层(flooding/bushfire/difficult topography/rail noise)用同法时返回非 JSON,**未跑通**;ANEF 0 条。
- 结论:Ipswich 现行 zone/overlay = ⚠️ 需浏览器开 isoplan eplan(或 Ipswich 的 Development.i,见第 7 节)。

### 2.7 其他 council
未逐一实测(超出本次范围):Gold Coast/Sunshine Coast/Moreton Bay/Logan/Ipswich/Brisbane 外的 QLD council(Redland、Toowoomba、Cairns、Townsville 等)——一般先搜 AGOL "{council} planning scheme zoning" 并核对 owner 是 council 官方账号;没有则开该 council 的 interactive mapping / property report。

---

## 3. 洪水

### 3.1 Brisbane(✅ 三层)
1. **规划 overlay(法定)**:Flags 里的 `FO`、`FHA_CK1-5`(Creek/waterway)、`FHA_R1-5`(Brisbane River)、`FO-OFF`(overland)。点查服务:`Flood_overlay_Creek_waterway_flood_planning_area`(字段 `OVL2_CAT`=FHA_CK4 等)、`Flood_overlay_Brisbane_River_flood_planning_area`、`Flood_overlay_Overland_flow`。
2. **Flood Awareness 概率图(2013 起,认知工具,非法定)**:`Flood_Awareness_Flood_Risk_Overall`、`_Creek`、`_River`、`_Storm_Tide`、`_Overland_Flow`、`Flood_Awareness_Extents` 等(同 org,点查模板)。官方说明:不提供水深/流速,深度须看 FloodWise Property Report。
3. **逐地块洪水位指标(= FloodWise Property Report 的数据底表)**:
```
curl -s -G "https://services2.arcgis.com/dEKgZETqwmDAh1rP/arcgis/rest/services/FAM_Property_Parcel_Metrics/FeatureServer/0/query" \
  --data-urlencode "where=LOTPLAN='{lotplan}'" -d "outFields=*&returnGeometry=false&f=json"
# 指标解码:FAM_Property_Parcel_Metrics_reference(METRIC/DESCRIPTION)
```
   指标读法:`20AEP/05AEP/02AEP/01AEP/002AEP_{RIVER|CREEK|ST}`=该地块最高洪水位(m AHD)+ `_C` 流域名;`FL_HIS1_*`=历史最高(含日期);`FL_DFL`=Defined Flood Level;`FL_HIGH/MED/LOW/VLOW_*`=概率分级标志;`OLF_FLAG`=overland flow;`MIN/MAX_GROUND_RL`、`EST_STR_FL`(估计habitable floor level)+ `_Q` 质量评级(C=较低)。**只有地块受影响时才有洪水位行;地块无洪水时只返回 ground RL/EST_STR_FL。**
- 实测 ✅ A(Denham,`112RP146054`):无 FO/FHA flag;FAM 仅 `MIN_GROUND_RL 10.6`、`MAX_GROUND_RL 17.3`、`EST_STR_FL 14.5`(质量 C);Flood overlay 三图层与 Flood Awareness 全 0 条 → **BCC 数据显示该地块无河/溪/overland/风暴潮洪水**。(最低地面 10.6m AHD。)
- 正例对照 ✅(Boondall `918RP894077`,933 m²):flags=`FO`、`FHA_CK4`、`FHA_CK5`、`PAS_A05`;FAM=1% AEP Creek 3.4m AHD(Nundah Creek)、20% 3.1、5% 3.2、2% 3.3、0.2% 3.3;历史最高 River 3.4(February 2022);风暴潮 1% 2.5(Moreton Bay);min ground 3.2/max 4.0;点查 `Flood_overlay_Creek_waterway_flood_planning_area` 命中 `FHA_CK5`。Flood_Awareness_* 图层在我取的内部点上 0 条(该点可能落在多边形外,**该图层正例未成功验证**,但 flags/FAM 表已证明数据链有效)。
- 判读注意:Flood overlay 的 FHA 分级以 flags 为准;**FAM 的洪水位是河道/溪流模型水位,要与 `MIN_GROUND_RL`/`EST_STR_FL` 比较**才能得出淹水深度;2022 年 2 月洪水按 FAM 有历史记录。overlay=规划触发,不代表一定淹。

### 3.2 其他 council
- Moreton Bay:`OM_Flood_Hazard_WebMercator_OpenData`(`FHA_FPA` Flood planning area 等)+ `OM_Overland_Flow_Path_...`;B1 无命中(未做正例对照)。
- Logan:图层 31(Flood assessment area)、39(Flood risk areas,含 Low/Flood investigation)等;B3 实测命中 Flood Assessment Area + Low Flood Risk Area。Logan 另有 FloodPortal 文件夹(`LoganHub` 旁 `FloodPortal` 目录,**未实测**)。
- Gold Coast:图层 81 "Flood assessment required";Sunshine Coast:图层 46。
- Ipswich:⚠️ 现行 overlay 须浏览器(2.6)。

### 3.3 州级:QFAO 与 FloodCheck
- **QFAO**(Queensland Floodplain Assessment Overlay):`https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Boundaries/AdminBoundariesFramework/MapServer/15`,只有 **118 个子流域多边形**(version 2.0,currency 2012 年),字段 `sub_name`、`version`、`currency`。**SEQ 市区几乎无覆盖**:Bremer River 子流域范围 lat -28.14~-27.72(Ipswich 市区 -27.62 在其外);Brisbane River 子流域范围到 lat -27.54;A/B1/B2/B3 与 Ipswich 市区点均 0 命中。正例 ✅:点 (152.353, -27.0035)(Somerset 附近)命中 `Brisbane River`,sub_number 1430,qra_supply Phase 1。**结论:QFAO 只对没有 council 洪水研究的区域有价值,SEQ 住宅不能依赖它,必须用 council 数据。**(州 SPP IMS 上的 Level 1 QFAO 在线展示未能访问,见第 4 节。)
- **FloodCheck**(DNRME,洪水研究索引,非洪水范围):`FloodCheck/FloodStudies/MapServer/2`(Flood Study – Level 3)。A 命中 3 条:"Cabbage Tree Creek Flood Study Upgrade Report"(Council,Complete)、"Gateway Motorway North Flood Study"(DTMR)等 → 说明哪些研究覆盖该地,可作「去哪里要研究报告」线索;**不给淹水范围/水位**。`FloodCheck/Floods_BrisbaneAndIpswich_1974`、`Floods_Brisbane_1893`、`2010To2011InterimFloodLines` 图层在 A 点 0 条。历史洪水线:`InlandWaters/FloodLines`(含 1974 Brisbane/Bremer、2011、2017 Logan/Albert 等;layer 12-19)未对测试点做正例,**未实测命中**。

---

## 4. 山火(州级 SPP bushfire prone area)

- 官方州级源:QFES 发布的「Bushfire Prone Area (July 2017)」,是 **瓦片服务**(`TilesOnly`,不能做 `/query`):`https://tiles.arcgis.com/tiles/vkTwD8kHw2woKBqV/arcgis/rest/services/Bushfire_Prone_Areas/MapServer`(owner PublicSafetyQld_Data;© State of Queensland QFES 2017, CSIRO)。方法:CSIRO 2014 报告(Very High/High/Medium 潜在山火强度 + 100m Potential Impact Buffer)。
- 州 SPP 互动制图系统(SPP IMS)的原 REST 域名 `spp.dsdmip.esriaustraliaonline.com`、`spp.dsdip.esriaustraliaonline.com` **DNS 已不存在**(实测 "Could not resolve host");`planning.statedevelopment.qld.gov.au` 本机 TLS 握手失败(WebFetch SSLV3_ALERT_HANDSHAKE_FAILURE,curl code 000)。州官方批量下载在 QSpatial 目录(SHP/FGDB,**未下载**)。
- **可复制的替代法:读瓦片像素(实测可用,"hack",不是正式 query)**。思路:算 z14 的 Web Mercator 瓦片 x/y 和像素,取 `.../MapServer/tile/{z}/{y}/{x}` 的 PNG 对应像素 RGBA;legend(`.../MapServer/legend?f=json`)色表(实测从 imageData 解码):Very High=(115,0,0);High=(230,0,0);Medium=(255,170,0);Potential Impact Buffer 在 legend 中为透明填充(只有轮廓)→ **buffer 区用像素法可能漏判**。alpha=0 即不在 BPA 内。瓦片 z16 返回 404(缓存只到 ≤z15),用 z14/z15。
  ```
  # python 片段(PIL):
  # x=int((lon+180)/360*2**z); y=int((1-asinh(tan(radians(lat)))/pi)/2*2**z); 取像素 (frac_x*256, frac_y*256)
  ```
- 实测 ✅:A(Denham)z14/z15 像素 alpha=0 → **不在州 BPA 内**;B1(Narangba)z14/z15 alpha=0;正例 Mt Coot-tha (152.95,-27.475) z14/z15 = (230,0,0,255)=High。
- 数据新旧:该瓦片是 **2017 年 7 月版**;现行 SPP 用版本可能更新,未能核实 → **结论只标「2017 版州 BPA 不覆盖」,报告须提示用 council overlay 复核**。
- Council 现行 overlay(更可靠、含现行版本):Brisbane `Bushfire_overlay`(正例 ✅:(152.95,-27.475) High hazard area `BHR_HRZ`;(152.93,-27.49) Medium `BHR_MRZ`;A 点 0 条);Moreton Bay `MBRC_PlanningScheme_OM_BushfireHazard`;Logan 图层 21;Gold Coast 图层 35;Sunshine Coast 图层 32/34。
- 另有 Logan 的 `OM-03.01 Bushfire hazard risk area`(Logan Hub),QFES 官方判读提示页(BPA 非地块级精确评估)等**未实测**。

---

## 5. 滑坡 / 酸性硫酸盐土 / 采矿

### 5.1 滑坡
- 州级:**未发现可点查的州级滑坡 REST 图层**(AdminBoundariesFramework/StatePlanning/其它文件夹均无),**未实测**。依赖 council overlay:
  - Brisbane:`Landslide_overlay`(字段 `OVL2_CAT=LH_LHZ`,"Landslide hazard");正例 ✅(点 153.3757255,-27.1429003 + distance=10 命中 2 条 `LH_LHZ`);A 点 0 条;flag=LO。
  - Moreton Bay `MBRC_PlanningScheme_LandslideHazardOverlay`(B1 0 条);Logan 图层 47-51(含 Historical landslide / ≥12% / ≥15% slope hazard;B3 0 条);Gold Coast 图层 95;Sunshine Coast 图层 58/59。

### 5.2 酸性硫酸盐土(ASS)
- Brisbane:flags `PAS`/`PAS_A05`(≤5m AHD)/`PAS_A20`(>5m <20m)/`PAS_ASZ`;点查图层 `City_Plan_2014_PotentialAndActual_acid_sulfate_soils_overlay`。**A=PAS_A20**(>5m,≤20m AHD;最低地面 10.6m)→ 开挖/填土 >100m³ 或 >…m 等触发条件须查 City Plan 对应 code(未实测条文)。
- 州级 SPP ASS:`Boundaries/AdminBoundariesFramework/MapServer/82`(State planning policy acid sulphate soils trigger area)实测 **只是 LGA 级粗标**(A/B3 点均命中同一个 BRISBANE CITY 多边形,`acid_sulph="Trigger area"`),**不能作地块判断**。SPP 地块级 ASS 为批量下载(QSpatial,未下载)。
- Logan 图层 3(`PAS_A20` 命中 B3)、Gold Coast 图层 12/13、Sunshine Coast 图层 0(Area 2)、Moreton Bay `MBRC_PlanningScheme_OM_AcidSulfateSoils`(B1 0 条)。

### 5.3 采矿 / 地下采矿 / 沉降
- **州级:Abandoned Mines(GeoResGlobe 同源)**:`https://spatial-gis.information.qld.gov.au/arcgis/rest/services/GeoscientificInformation/AbandonedMines/MapServer`。图层(实测):62 Underground workings outline;63 Underground Workings;45 Mine openings;105 Shallow workings area;110 Mine openings area;25 Urban remediation areas;75 Shallow working(point);85 Pit。命令(推荐"附近 500m",因为地下 outline 可能在地块外):
```
curl -s -G ".../AbandonedMines/MapServer/62/query" -d "geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&distance=500&units=esriSRUnit_Meter&outFields=mine_name,mine_no,plan_no,rehab_yr&returnGeometry=false&f=json"
```
- 实测 ✅ B2(Redbank,Ipswich):点内相交均 0 条,但 **500m 内 Underground workings outline 命中 3 个**:PIONEER MINE(约 199m,mine_no 21)、REDBANK COLLIERY(约 329m,mine_no 45)、WESTFALEN NO.3 COLLIERY(约 456m,mine_no 40);rehab_yr=0。A(Denham)500m 内 0 条。
- 判读:Redbank/Goodna/Bundamba 属 Ipswich 煤田老矿区,**邻近 ≠ 地下正下方**,outline 是历史记录精度;精确是否在 workings 之上、是否有 subsidence 须查 Ipswich City Plan 2025 的 mining overlay(浏览器,见 2.6)及 GSQ 报告(如 "KEY RESOURCE AREAS AND UNDERGROUND MINING AS PLANNING CONSTRAINTS IN THE CITY OF IPSWICH",data.qld.gov.au 条目 cr088799,**仅检索到条目,未读正文**)。过期的 2006 版 OV3 mining buffer 也命中 B2(见 2.6)。
- Brisbane `Extractive_resources_overlay_*`(Key resource route/Mining tenement)、Moreton Bay `..._ExtractiveResources_Overlay`:A/B1 0 条(只代表采石资源 overlay,与地下旧矿不同)。GeoResGlobe 网页:https://georesglobe.information.qld.gov.au(**未打开**,用上面 REST 即可)。

---

## 6. 官方估价(Valuer-General 土地估价)

- 官方免费逐地块入口(都是人工网页):
  1. "Find your land valuation"(按地址/Property ID):https://www.qld.gov.au/environment/land/title/valuation/find-your-land-valuation(页面自述受 reCAPTCHA 保护;后端 `apps.resources.qld.gov.au/valuations/land-valuations/` 对脚本直接断连 `RemoteDisconnected`)。
  2. Queensland Globe「Land valuations」topic:https://qldglobe.information.qld.gov.au/?topic=land-valuations-information-on-queensland-globe(官方页面说明:显示 Property ID(白)、当前估价(金)、新估价(绿);**不对 community title 单元单独估价,只给整体**)。
- 开放数据:data.qld.gov.au「Valuation Property Boundaries – Queensland」(CC-BY 4.0,2026-10-02 更新,是估价册 QVAS 的地块空间化)只有 **FGDB 批量下载**(QSpatial 目录),**没有 REST/WFS**;`spatial-gis` 全部 164 个服务逐个核对名称无 valuation 服务。`LandParcelPropertyFramework` 图层 50 "Properties" 是命名物业,**没有估价字段**。
- 判定:**⚠️ 免费逐地块估价需浏览器人工看(Qld Globe 或 find-your-land-valuation 页);不可自动化(reCAPTCHA / 无 REST)。** 我没有绕过 CAPTCHA,也没做批量下载。
- 判读注意(来自官方页面):土地估价是 **land value(非房价)**;QLD 非农村按 site value,农村按 unimproved value;各 LGA 估价日不同(2026 年估价已发布,另有 2027 页面)。可比价请用成交证据而非估价。

---

## 7. DA / 开发活动

| council | 公开平台 | 实测 |
|---|---|---|
| Brisbane | Development.i https://developmenti.brisbane.qld.gov.au (按地块/地址/地图搜索) | 站点 200;`/Home/FilterDirect?filters=...` 返回页面框架;页面 JS 调 `/Geo/GetApplicationFilterResults`(GET 404,**参数未知、官方无 API 文档**,未再试以免滥用);BCC Open Data(Huwise v2.1,446 个 dataset)搜索 "development application(s)/approvals" **无 DA 数据集**。→ ⚠️ 浏览器 |
| Ipswich | Development.i https://developmenti.ipswich.qld.gov.au | 站点 200;同类 Development.i 平台 → ⚠️ 浏览器 |
| Sunshine Coast | https://developmenti.sunshinecoast.qld.gov.au | 站点 200 → ⚠️ 浏览器 |
| Moreton Bay | PD Online(pdonline.moretonbay.qld.gov.au) | 本机连接失败(HTTP 000)→ **未实测**,⚠️ 浏览器 |
| Logan | pdonline.logan.qld.gov.au | 本机连接失败(HTTP 000)→ **未实测**,⚠️ 浏览器 |
| Gold Coast | pdonline.goldcoast.qld.gov.au | 301 重定向 → **未实测**,⚠️ 浏览器 |

结论:**❌ 没有免费公开的 DA 查询 REST/批量接口(至少未找到)。** 做法:报告里列「去查该地址 + 邻近地块 5 年内的 DA(拆建、dual occupancy、multiple dwelling)」的人工清单与入口 URL;不做自动抓取。

---

## 8. 道路车流量(AADT)、铁路、机场 ANEF、州交通噪音走廊

### 8.1 AADT(TMR)
- 来源:`Transportation/StateRoadInformation/MapServer`,AADT 图层按年:**最新图层=46 "Average annual daily traffic 2020"**(其余:44=2019、42=2018、36=2017…)。2025 数据在 data.qld.gov.au「Traffic census for the Queensland state-declared road network」(2026-08-06 更新,有 `aadt_2025.xlsx`、`trafficcensus2025.kml`),**未下载**(下载需单独授权/本次未做)。
- 命令(找最近站点;AADT 站点只在 **州管路**上):
```
python near.py "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Transportation/StateRoadInformation/MapServer/46" {lon} {lat} 3000
# 等价 REST:.../46/query + distance=3000&units=esriSRUnit_Meter&outFields=*&returnGeometry=true&outSR=4326 然后自行算距离
```
  字段:`aadt`、`percent_hv`(重车%)、`description`、`road_name`、`latitude/longitude`。
- 实测 ✅ A:Denham St 本身是 local road,**800m 内无 AADT 站点**;3km 内 4 个:SANDGATE SUB-ARTERIAL ROAD "Deagon Deviation north of Depot Road" 约 1.25km,AADT **20,731**(HV 8.76%);"U88 - Braun St at Biarra St" 约 1.72km,**25,505**;"At Gateway On ramp" 约 2.13km,**27,656**;LINKFIELD CONNECTION ROAD 约 2.94km,**30,099**(HV 11%)。州管路最近:GATEWAY ARTERIAL(Gateway Motorway)约 763m(图层 6 "State controlled road")。注意 2020 年数据偏旧。
- 判读:A 所在街不能用 AADT 判噪音,因为本街是 local road(BCC 自有路无开放 AADT,**BCC traffic count 未找到开放数据**)。

### 8.2 铁路
- `Transportation/OtherTransport/MapServer`:156 Railways;101 Train station(Translink 站台,含 `stop_name`、`route_type`);150 组。
- 实测 ✅ A:最近铁路 **Shorncliffe Line 约 1,918m**(electrified,passenger,operational;route_name "Shorncliffe Line",section "Bowen Hills to Shorncliffe");Caboolture/Sunshine Coast Line 约 2,265m;North Coast Line(Freight-Passenger)约 2,279m。最近车站:**Deagon 约 2,078m**、North Boondall 约 2,216m、Carseldine 约 2,575m。距离用 `near.py` 取线/点最近顶点算 haversine(顶点近似,线中段可能更近)。

### 8.3 机场 ANEF
- Brisbane:BCC `City_Plan_2014_Airport_environs_overlay_Australian_Noise_Exposure_Forecast_ANEF`(**多边形** ANEF 20/25/30/35/40/45,字段 `OVL2_CAT`=ANF>20 等;flags 里 `ANF>20…ANF>40` 对应)。
- 实测 ✅ A:点内 0 条;8km 内最近 ANEF 20 轮廓约 **7.5km**、ANEF 25 约 7.9km → **A 不在 ANEF 20 以内**(A 的 flags 只有 AEO 机场环境 overlay + BSZ_D13 鸟蝠撞击区 + OLS 高度限制面)。
- Logan 图层 68-70(Strategic airport and environs)、Gold Coast 图层 94、Sunshine Coast 图层 12/18、Ipswich(2006 版 OV7C ANEF 对 B2 0 条;现行版须浏览器)。
- 判读:ANEF 20 以内才进入住宅声学要求/披露关注区;AEO 覆盖面大得多,不等于噪音。

### 8.4 州交通噪音走廊(TMR/SPP,Queensland Development Code MP4.4)
- Brisbane:flags `TNC`、`TNC_LG1-4`(local road category);点查 `Transport_noise_corridor_overlay`,以及 `City_Plan_2014_Transport_noise_corridor_overlay_State_controlled_road_centreline`(中心线,A 附近 763m 有 TNC_CLM "state-controlled road (mandatory area)" 中心线,但 A 地块本身无 TNC flag → **不在噪音走廊内**)。
- 州批量下载:data.qld.gov.au "Transport Noise Corridors – State Controlled Roads – Mandatory/Voluntary/centreline"(SHP/FGDB,**未下载**)。
- Logan 图层 74(State-controlled road mandatory,B3 实测命中 Category 1)、75(Railway)、73(local road);Moreton Bay `MBRC_PlanningScheme_TransportNoiseOverlay`(B1 0 条)。

---

## 9. 政策红利(只认官方原文,带生效日期)

| # | 政策 | 官方原文/证据 | 日期 | 适用 A? |
|---|---|---|---|---|
| 1 | **Brisbane City Plan "More Homes, Sooner – Low-medium density residential design"(City Plan Amendment v37.00/2026)** | 页面原文:"The amendment was adopted by Council on 18 August 2026";"became effective in City Plan on 18 September 2026 as part of City Plan Amendment v37.00/2026"。条文:small lot house 最高 "3 storeys and 11.5m";"a minimum lot size of 120m2 where meeting design and built form criteria"(分割阶段评估);dual occupancy "a minimum lot size of 400m2";multiple dwellings 在 Key Locations 可达 "4 storeys and 14m"(最小地块 800m²);"a total site cover of 55% for lots under 180m2";"a maximum impervious area of 70%"。 来源:https://www.brisbane.qld.gov.au/building-and-planning/planning-and-design/city-plan-amendments/low-medium-density-residential-design (WebFetch 2026-10-03) | 通过 2026-08-18;生效 2026-09-18 | **A 是 LDR 不是 LMR,本条不直接适用**;且 A 带 DHO 住宅特色 overlay |
| 2 | **QLD 次要住宅(Secondary dwelling,granny flat)可出租给任何人** | 官方立法 Planning (Secondary Dwellings) Amendment Regulation 2022(SL 2022 No. 133)原文定义:"secondary dwelling means a dwelling on a lot that is used in conjunction with, but subordinate to, another dwelling on the lot, whether or not the dwelling is— (a) attached to the other dwelling; or (b) occupied by individuals who are related to, or associated with, the household of the other dwelling." 来源:https://www.legislation.qld.gov.au/view/pdf/asmade/sl-2022-0133(已读出全文) | 生效日:planning.qld.gov.au 页面搜索摘要称 **2022-09-26**(该页面本机 WebFetch 403,**生效日未能直接读到正文,标「待核」**)https://www.planning.qld.gov.au/planning-issues-and-interests/changes-to-secondary-dwellings | 适用,但**不免除** council 开发许可/建筑审批;A 的 DHO 对新建/拆建 secondary dwelling 的限制须读 City Plan 条文(未读) |
| 3 | **Ipswich City Plan 2025 取代 2006 规划方案** | 官方页面原文:"adopted by Council on 29 May 2025" / "took effect on 1 July 2025"(https://www.ipswich.qld.gov.au/Services/Planning-and-Building/Planning/Planning-in-Ipswich) | 2025-07-01 生效 | 与 A 无关;**对 B2 意味着开放数据过期** |
| 4 | **Brisbane Housing Supply Incentive Policy (AP290)** | BCC housing supply 页面(WebFetch 摘要):"reduced infrastructure charges" for eligible developments in growth areas;页面标 "Last modified 1 July 2025"(**此为页面修改日,非政策生效日,标「待核」**)https://www.brisbane.qld.gov.au/building-and-planning/planning-and-design/housing-supply | 待核 | 条件未读,无法判 A |

- 未覆盖(未检索/未验证,别写进报告):QLD 州「small lot / LMR / dual occupancy」其他州级法规、Brisbane DHO 在 v37 是否改动、stamp duty/transfer duty 优惠(非规划类)。DHO 与 LDR 的 v37 条文本次**未读**。

---

## 10. 测试地址实测结果汇总表

| 检查项 | A: 56 Denham St Bracken Ridge (Brisbane) | B1: 20 Steven Ct Narangba (Moreton Bay) | B2: 30 Brisbane Rd Redbank (Ipswich) | B3: 25 Station Rd Loganlea (Logan) |
|---|---|---|---|---|
| 地址→坐标 | ✅ 153.042138,-27.327258 (98.62) | ✅ 152.955423,-27.199764 (98.57) | ✅ 152.865045,-27.602217 (98.57) | ✅ 153.125298,-27.66951 (98.57) |
| 地块 | ✅ 112RP146054 698㎡ Freehold Base | ✅ 21SP191127 500㎡ Base | ✅ 1RP127017 756㎡ | ✅ 6RP110606 809㎡ |
| strata? | 否(Base,单条) | 否(Base) | 否 | 否 |
| Zone | ✅ LDR + Bracken Ridge NP(无 precinct) | ✅ General residential / Urban neighbourhood | ⚠️ 现行须浏览器(2006 版仅示范) | ✅ Low Density Residential / Small Lot precinct |
| 关键 overlay | DHO、PAS_A20、AEO、OLS、SHO、RHO、CIO | 车站 800m 圈(WDTS800);其余 0 | ⚠️ 2006 版:OV3 Mining Constrained Area | ASS A20、Flood assessment area、Low flood risk、TNC Cat1 州路 |
| 洪水 | ✅ 无(最低地面 10.6m,EST_STR_FL 14.5) | ✅ 0 命中(无正例对照) | ⚠️ 浏览器 | ⚠️ 命中 Flood assessment + Low risk |
| 山火(州 2017 BPA 瓦片) | ✅ 不在 | ✅ 不在 | 未测 | 未测 |
| 滑坡 | ✅ 无 | 0 | 未测 | 0(slope 图层) |
| ASS | PAS_A20 | 0 | 未测 | PAS_A20 |
| 地下采矿(Abandoned Mines 500m) | ✅ 无 | 未测 | ✅ Pioneer 199m / Redbank Colliery 329m / Westfalen 3 456m | 未测 |
| 官方估价 | ⚠️ 浏览器(Qld Globe/Find your land valuation) | 同 | 同 | 同 |
| DA | ⚠️ Development.i 浏览器 | ⚠️ PD Online(连不上) | ⚠️ Development.i | ⚠️ PD Online(连不上) |
| AADT(2020 最近站) | 本街无;Sandgate Rd 1.25km 20,731 | 未测 | 未测 | 未测 |
| 铁路 | Shorncliffe Line 1.9km;Deagon 站 2.1km | (WDTS800 示 Narangba 站 ≤800m) | 未测 | 未测 |
| ANEF | 不在(ANEF20 约 7.5km) | 未测 | 2006 版 0 | 未测 |
| 州噪音走廊 | 不在 | 0 | 未测 | ✅ 命中 Category 1 |

(Gold Coast B4:Medium density residential 2 (9m)/PAS_A05/Flood assessment required/Dwelling house overlay;Sunshine Coast B5:Tourist Accommodation Zone/ASS Area 2——仅验证图层可用。)

---

## 11. 未解决 / 存疑清单

1. **州级 SPP 官方查询端点缺失**:SPP IMS 的 REST 域(spp.dsdmip/dsdip.esriaustraliaonline.com)DNS 已不存在;planning.statedevelopment.qld.gov.au 本机 TLS 失败。州级 SPP 山火/ASS/QFAO/洪水/滑坡 Level 1 在线图层**无法从脚本确认**。需到浏览器(Qld planning "SPP interactive mapping system")确认一次,或下载 QSpatial 批量包(本次未下载)。
2. **州山火瓦片是 2017 版**;Potential Impact Buffer 在像素法下可能漏判;须与 council overlay 交叉。
3. **QFAO 在 SEQ 市区基本无覆盖**(118 多边形,2012 版);不要把「QFAO 无命中」解读为无洪水。
4. **Ipswich 现行 zone/overlay**:isoplan 对脚本 403;data.gov.au 开放数据全是 superseded 2006 版。Ipswich 住宅尽调当前只能人工看 isoplan(或让用户导出 property report)。
5. **估价**:无 REST/开放逐地块源,reCAPTCHA;`apps.resources.qld.gov.au` 对脚本断连。仅人工。
6. **DA**:无开放接口;MB/Logan/GC PD Online 本机连不上(000/301),未判断是否有公开接口。
7. **AADT 仅到 2020**(REST);2025 在 xlsx/KML 批量文件(未下载)。BCC 自有路无开放流量。
8. **BCC Flood Awareness 概率图层正例**未成功命中(取点可能出多边形),flags/FAM 表证明数据链有效但「图层级正例」未验证;**MB 洪水层也无正例对照**。
9. **Brisbane DHO / LDR 条文**(拆建、dual occupancy、secondary dwelling 在 DHO 地块的限制)与 v37 对它们是否有改动:**本次未读条文**。A 的开发潜力结论暂不能给。
10. **政策日期待核**:secondary dwelling 生效日 2022-09-26 仅来自搜索摘要;AP290 的「Last modified 2025-07-01」不是生效日;Logan 的 DRAFT 规划方案(20250821)状态未核。
11. 未验证:`Zoning_opendata` 是否标明 v37(仅 `dataLastEditDate` 2026-09-17 吻合);`PCF53`/`Grid` flag 含义;MB `gis-cl6.moretonbay.qld.gov.au` 官方服务;Logan Property Report/FloodPortal 服务;GTP 前缀样本。
12. 共享 scratchpad 被其他会话覆盖过 `q.py`(其它州 agent);本说明脚本在 `scratchpad\qld\` 子目录,别用顶层 `q.py`。
