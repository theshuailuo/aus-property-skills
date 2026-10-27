# Northern Territory(NT)辖区适配说明 · auspptdd

- 实测日期:2026-10-03(本机 curl / Python / Browser pane)
- **测试地址**:80 Nightcliff Road, Rapid Creek NT 0810(Nightcliff 一带;地籍 = Lot 00567 Town of Nightcliff,Darwin Mid Suburbs Area Plan)
  - 选择理由与偏差声明:Palmerston/Nightcliff 没有可 curl 的官方地块 REST,**我是从 NT 官方 Planning Notices Online 的在审 DA JSON 里挑了一个住宅地址**(能同时拿到地块描述和分区),所以该地址恰好有一个在公示的 DA(PA2026/0344)。对「一般地址」的可复用性要看 §1。
- **测试坐标(WGS84)**:lon = 130.85216214,lat = -12.38018897(来源=NTG 托管的 "Northern Territory Locator"(ArcGIS 地理编码服务,item owner `ntlisadmin`),Score 100,PointAddress)
- **NT 是三个辖区里「官方免费空间 REST 接口最差」的一个**:没有找到 TAS(LIST)/ACT(ACTmapi)那样可点查的 zone/cadastre/overlay 服务。官方入口主要是:
  1. **NT Atlas and Spatial Data Directory**(旧版 IMF 地图视图)http://www.ntlis.nt.gov.au/imfPublic/imf.jsp?site=nt_atlas —— 页面实测可打开(Browser pane),但不暴露可 curl 的 REST;
  2. **Planning Notices Online** JSON(**可 curl**,但只含「当前在公示」的申请)https://www.ntlis.nt.gov.au/planning-notices-online/notices ;
  3. **data.nt.gov.au**(CKAN)上的 **shapefile/GDB 整包下载**(storm surge、flood study、traffic report 等),需要下载后本地做点在面内。
- 全局注意:`nt.gov.au`、`ntlis.nt.gov.au` 大部分页面对 curl 返回 Cloudflare 403("Just a moment...")——**curl 通过的**:`data.nt.gov.au` CKAN API、`ftp-dlrm.nt.gov.au` 下载、`www.ntlis.nt.gov.au/planning-notices-online/notices/json`;**其余用 Browser pane(可过 Cloudflare)**。

---

## 1. 地址 → 坐标 → 地块(lot/portion、面积、边界、strata)

### 1a 地址 → 坐标
- 来源:NTG "Northern Territory Locator"(ArcGIS GeocodeServer,通过 utility.arcgis.com 代理,item 由 NTG 的 ArcGIS Online 账号 `ntlisadmin` 发布,**非文档化公共 API,可能随时失效**)
- 命令:
```bash
curl -s -G "https://utility.arcgis.com/usrsvcs/servers/cf8a5ae23b744586a004928b9e9daa8c/rest/services/World/GeocodeServer/findAddressCandidates" \
  --data-urlencode "SingleLine={STREET_NUMBER} {STREET} {TYPE}, {SUBURB} NT {POSTCODE}" \
  -d "outSR=4326&maxLocations=3&outFields=*&f=json"
```
- 返回:`candidates[0].location.x/y`(= lon/lat),`score`,`attributes.Addr_type`(PointAddress=门牌点)。
- 实测状态:✅ `80 Nightcliff Road, Rapid Creek NT 0810` → x=130.85216214, y=-12.38018897,score 100,Addr_type PointAddress,Match_addr "80 Nightcliff Road, Rapid Creek, Darwin, Northern Territory, 0810"。
- 备用(**非官方**,仅作坐标兜底):OpenStreetMap Nominatim 对同一地址只返回道路中心(-12.3847, 130.8558,class highway),**精度不足,仅街道级**。
- 注意:G-NAF(Geoscape)是整包下载(data.gov.au),本次未用。

### 1b 坐标 → 地块(Lot/Section/Portion)
- ❌ **未找到免费可 curl 的 NT 地籍(parcel)REST/WFS**。已试路线(≥3 条):
  1. 猜测并实测 NT 政府 ArcGIS Server 主机(maps.nt.gov.au / mapservices.nt.gov.au / services.ntlis.nt.gov.au / ntgis.nt.gov.au / ntlis.nt.gov.au/arcgis/rest / nrmaps.nt.gov.au/arcgis/rest 等):无响应或 404 / Cloudflare;
  2. data.nt.gov.au CKAN 搜 cadastre/lots/land parcels:**没有地籍数据集**(返回的是土地资源调查、水资源、Mineral Titles 等);data.gov.au 搜索同样无 NT 地籍;
  3. NTG 的 ArcGIS Online 账号 `ntlisadmin`(共 38 项)只有 Alice Springs 区域规划图、Darwin CBD 等 StoryMap/FeatureServer(如 `Map_2___Town_Planning_Zones_WFL1`,**仅 Alice Springs**),无 Territory-wide cadastre;
  4. NT Atlas(IMF,Browser pane 实测可打开)/ NR Maps(`nrmaps.nt.gov.au`,Geocortex,请求为 `/server/request/execute.do` 私有协议)都不暴露标准 REST。
- **可得的地块描述(仅限「当前在公示的申请」)**:Planning Notices Online JSON 的 `parcelDetails`:`landDescription`("Lot 00567 Town of Nightcliff")、`parId`(550000567)、`streetNumber/streetName/streetType/suburb`、`townPlanZoneCode`、`parcelOverlays`、`strategicFramework`(Regional Land Use Plan / Area Plan)。
- 兜底:人工 NT Atlas(http://www.ntlis.nt.gov.au/imfPublic/imf.jsp?site=nt_atlas)或向 NT Land Titles Office 查询(收费,未实测)。
- 实测状态:⚠️ **地块面积/边界/strata:未取得**。测试地址只拿到 "Lot 00567 Town of Nightcliff"(来自 DA 公示),**没有面积、没有边界**。
- strata/unit title:NT 的 unit title 在 Land Title Act;**免费图层未找到**。该 DA 的 purpose 写 "existing dwelling-group"(group dwelling),提示该 lot 上可能是多户/分契,**但 strata 状态未验证**。

---

## 2. 规划分区 zone + overlays(含 heritage)

### 2a Zone(NT Planning Scheme 2020)
- 官方指引原文(https://nt.gov.au/property/land-planning-and-development/our-planning-system/nt-planning-scheme/understand-the-nt-planning-scheme/zones ,2026-10-03 取得):"To find the zone, you can: use the 'town planning' zones layer on NT Atlas; contact a planner from Development Assessment Services." → 即官方推荐入口是 **NT Atlas 的 town planning zones 图层(浏览器)**。
- 可 curl 的唯一路径(**仅覆盖在公示 DA 的地块**):
```bash
curl -s -A "Mozilla/5.0" "https://www.ntlis.nt.gov.au/planning-notices-online/notices/json" -o notices.json
python - <<'EOF'
import json
j=json.load(open('notices.json'))
for n in j['currentNotices']:
    for p in n['parcelDetails']:
        print(n['applicationNumber'], p['landDescription'], p.get('streetNumber'), p.get('streetName'), p.get('suburb'),
              p['townPlanZoneCode'].strip(), p['townPlanZoneDescription'], p['parcelOverlays'])
EOF
```
  (没有服务端筛选参数的证据,**取全表再本地过滤 suburb/street**;`currentNotices` 实测 15 条。)
- 返回字段读法:`townPlanZoneCode`(LMR / LR / MR / GI / C / SD31 / CP / RL / NOZONE …,带尾部空格,要 strip)、`townPlanZoneDescription`;`strategicFramework.areaPlan`(如 "Darwin Mid Suburbs Area Plan");`parcelOverlays[]`(`id`+`type`)。
- 实测状态:✅(仅针对该地址所挂的在审 DA)测试地址 **Lot 00567 Town of Nightcliff,`townPlanZoneCode "LMR"`,Low-Medium Density Residential**,`areaPlan "Darwin Mid Suburbs Area Plan"`,`parcelOverlays []`。
- 判读注意:
  1. 这是 **DA 申请时挂接的地块属性**,不是通用查询接口;**没有在审 DA 的地址拿不到**。
  2. skill 里对 NT 的默认动作:直接输出 ⚠️「需人工在 NT Atlas 查 zone」+ 入口 URL,并说明如何用 Notices JSON 做「是否正在公示」的旁证。
  3. Zone 的使用规则(最小地块、停车、Group/Multiple dwelling 条件)见 NT Planning Scheme 2020 Part 4(PDF:https://nt.gov.au/_media/docs/housing,-property-and-land/planning-and-development/nt-planning-scheme-2020/part-4-zones-and-assessment-tables-nt-planning-scheme-2020.pdf ,链接取自 nt.gov.au 页面,**PDF 本身未取回**)。

### 2b Overlays
- NT 规划方案的 overlay 在 DA 公示里以 `parcelOverlays[].type` 出现。**本次在 15 条公示中实测见到的类型**:
  - `LPA - Land in Proximity to Airports`(Lot 09742 Town of Nightcliff,107 Dick Ward Dr, Coconut Grove;id 形如 `LPA67826`)
  - `LSSS - Land Subject to Storm Surge`(id `LSSSSECONDARY`;见于 N.T. Portion 01646 West Arnhem 与 Section 07350 Hundred of Bagot, Tivendale)
  - `CNV - Clearing of Native Vegetation`、`DHD - Darwin Harbour Dredging`
- 测试地址:`parcelOverlays []`(无 LPA、无 LSSS)。
- 命令:同 2a 的 JSON。
- 判读注意:**overlay 清单只能是「在公示 DA 里出现过的」,不是全集**;NT Planning Scheme 2020 里 overlay 的完整名单需读方案文本(未实测)。**不得据此推断「无 bushfire/flood overlay」**。

### 2c Heritage
- ❌/⚠️ **未找到免费 heritage 空间服务**:data.nt.gov.au CKAN 搜 "heritage" = 0;NT Heritage Register 在 Heritage Branch(DLPE)网站,未实测。
- 人工:NT Heritage Register 入口未实测;**在 skill 里标 ⚠️「需人工看 NT Heritage Register / Aboriginal Areas Protection Authority(AAPA)sacred sites」**(AAPA 为另一机构,未实测)。

---

## 3. 洪水(含 NT storm surge)

### 3a Storm surge(风暴潮)——官方整包数据,本地点在面内
- 来源:data.nt.gov.au 数据集 **"Darwin Region Storm Surge mapping"**(DLPE;CKAN id `darwin-region-storm-surge-mapping`,修改日 2021-06-22)
  数据集页:https://data.nt.gov.au/dataset/darwin-region-storm-surge-mapping
  下载(直接 URL,实测 HTTP 200,Content-Length 28,982,929 字节,Last-Modified 2023-11-27):
  `https://ftp-dlrm.nt.gov.au/main.html?download&weblink=dbc951e000d6b091daf0fca539aac12d&realfilename=WaterInundation_stormsurge_dwn_25.zip`
- 包内容(实测解压):`data/dwn_2100_100.shp`(**2100 年 100 年一遇 ARI**,projection year 2100)、`dwn_2100_1000.shp`(2100 / 1000 年 ARI)、`dwn_2100_bnd.shp`(研究范围边界);`products/Maps/*.pdf`(Darwin/Palmerston/Cox-Peninsula/Bynoe/Dundee/Weddell 2100 storm surge 图 Oct-2014);`products/Report/Darwin Storm Tide Mapping Study 2006.pdf`。**`.lyr` 文件引用了 10000 年 ARI 与 HAT,但 shp 不在包里**;**包里没有当前气候(2010 基线)情景**。属性:`STUDY_NME "Darwin Storm Tide Mapping Study"`,`SCALE 25000`,`PRJ_YR 2100`,`ARI "100 Year"/"1,000 Year"`,`DATA_DATE "OCT 2014"`,坐标系 GCS_GDA_1994(经纬度)。
- 点在面内命令(Python,需 `pip install pyshp`;纯 Python 射线法,无需 GDAL):
```python
import shapefile
def pip(x,y,shape):
    pts=shape.points; parts=list(shape.parts)+[len(pts)]; inside=False
    for a,b in zip(parts[:-1],parts[1:]):
        ring=pts[a:b]; n=len(ring); j=n-1
        for i in range(n):
            xi,yi=ring[i]; xj,yj=ring[j]
            if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi: inside=not inside
            j=i
    return inside
sh=shapefile.Reader("dwn_2100_100").shape(0)   # 整个研究区只有 1 个多部件面
print(pip({lon},{lat},sh))
```
- 实测状态:✅
  - 测试地址 (130.85216214, -12.38018897):**2100 年 100 年一遇 与 1000 年一遇 均不在淹没范围内**(False);离最近多边形顶点约 **487 m**(顶点近似,偏保守)。
  - 阳性对照(陆地):(130.864, -12.380)(Rapid Creek / Ludmilla 潮溪一带)**在 2100/100 年一遇范围内**(沿 -12.380 的格点扫描:X 命中位于 lon≈130.862–130.866,分布与潮溪走向一致);海面点全部命中(研究区面包含海域)。
- 判读注意:
  1. **这是 2100 年气候变化情景图,不是当前风险**;当前基线(2010)未在此包内,**不要把 2100 范围当作「现状会淹」**。
  2. 研究区是 1 个多部件大多边形,点在面内用 even-odd 即可;陆地/海域不分——**命中点在海里并不说明什么,要看是否落在陆地地块**。
  3. 研究范围外(如 Palmerston 以外、Gulf)用别的数据集:`gulf-of-carpentaria-storm--tide-and-inundation-study`、`nt-remote-communities-storm-tide-study-and-inundation-mapping`(CKAN 列出,未下载)。
  4. 数据 ≥2014 年版;NT 规划里的 `LSSS - Land Subject to Storm Surge` overlay 是法定口径(见 §2b),**与此 shapefile 不一定同一套划分**。

### 3b 内陆洪水
- data.nt.gov.au 有:`elizabeth-and-blackmore-river-catchments-flood-study`、`alice-springs-flood-investigation-and-floodplain-mapping-study`(shapefile 整包;**Nightcliff/Rapid Creek 不在这两个研究区内**),Darwin 都会区内陆洪水(如 Rapid Creek / Sadgroves Creek 流域)图:**未找到公开数据集**。
- 状态:⚠️/❌ Nightcliff 一带**无免费洪水图**可得;人工:City of Darwin / Palmerston 市政府洪水说明(未实测)。

---

## 4. 山火(bushfire-prone areas)

- ❌ 未找到 NT 官方「bushfire-prone area」规划图层。data.nt.gov.au 有 Bushfires NT 的 Administration Boundaries、Burn Permits、Brigade 位置、**NT Fire History**(CKAN `nt-fire-history`,多格式整包下载含 GPKG/GDB,未下载)、"Bushfire Risk for Remote Communities"(偏偏远社区),**不是住宅规划法定图**。
- Darwin 市区(Nightcliff 近海、已建成城区)的山火风险在规划方案中是否有 overlay:**未验证**(2b 的 overlay 类型里没见到 bushfire)。
- 状态:❌ 无免费等价物;测试地址不判。

---

## 5. 滑坡 / 酸性硫酸盐土 / 海岸侵蚀与淹没 / 其它

- 滑坡:Darwin 地形平缓,**本说明不测**;❌ 无源(未找到)。
- 酸性硫酸盐土:data.nt.gov.au 搜 acid/sulfate = 0;**❌ 未找到**(Darwin 沿海有 ASS 风险是常识,**但无官方免费图层可引**)。
- 海岸淹没:见 §3a(storm surge,2100)。海岸侵蚀:**未找到**。
- 其它相关 CKAN 数据集(整包):`erosion-hazard-restricted-use-areas-under-soil-conservation-act`、`northern-territory-dryland-salinity-hazard-risks`(均 Soil/土地管理,**不是都会区住宅口径**),`greater-darwin-land-suitability`(未下载)。
- 白蚁/气旋等级:NT 特有的 **cyclone region C 建筑规范**(建筑法规,非图层)——**不属于本接口范围**。

---

## 6. 官方估价(UCV)

- 官方机制(https://nt.gov.au/property/homeowners-and-landlords/understanding-your-property-valuation/statutory-valuations ,2026-10-03 取得):
  - "Within the general valuation cycle, a Territory-wide valuation of UCV is made for all rateable land at least every three years."
  - "The general valuations are dated 1 July of the year the work is carried out. This is the effective date."
  - 计划重估:页面写 "2026 - City of Darwin, City of Pa..."(原文在此处被截断,**应为 City of Palmerston,未核实**)。2025 年:Katherine/Coomalie/Wagait。
  - UCV 定义(WebSearch 摘要引 nt.gov.au):the amount land alone would sell for without above-ground improvements。
- **公开逐地块查询:❌ 无**。该页只提供 "valuations online portal"(**注册需要 notice of valuation 与当前邮箱**,原文:"You will need your notice of valuation and a current email address to register"),即**业主自助**;"Get previous UCVs" 要到 Valuation Services 办公室或邮件/电话:valuation.services@nt.gov.au,08 8999 6054(Valuation Services,18–20 Cavenagh Street, Darwin City)。
- data.nt.gov.au CKAN 搜 valuation = 0 个数据集。
- 另:LGANT 有一份 "Valuation Data NTG" PDF(搜索结果,**未取得、未读**)。
- 状态:❌ 无免费逐地块 UCV;skill 里输出「UCV 需业主 notice/向 Valuation Services 申请」。

---

## 7. DA / 开发活动公开接口

- ✅ **有官方公开接口**:Planning Notices Online(NTG,Development Consent Authority 公示)
  - 页面:https://www.ntlis.nt.gov.au/planning-notices-online/notices
  - JSON:`https://www.ntlis.nt.gov.au/planning-notices-online/notices/json`(curl 带 `-A "Mozilla/5.0"` 实测 HTTP 200,application/json,68 KB)
  - 顶层键:`appTypes`(D Development / S Subdivision / PS Planning Scheme Amendment / ED Exceptional Development / CA Concurrent Application)、`suburbs`、`poboxTypes`、`currentNotices`、`planningNoticeSubscriptions`、`siteKey`、`videoProps`。
  - `currentNotices[]` 字段:`applicationNumber`(如 PA2026/0344)、`purpose`、`applicationType`、`assessmentCategory`、`variations`、`parcelDetails[]`(地块 + zone + overlays)、`documents`(分类附件;URL 在 JSON 里写成 `https://localhost/planning-notices-online/planningPopup/lta.dar.viewDocument/{applicationId}?docId={id}`,**实际要把 host 换成 `www.ntlis.nt.gov.au` 才能访问;文件下载未测**)、`consentAuthority`(DCA Darwin Division 等)、`exhibition`(startDate/finishDate)、`applicants[].name`、`office`(联系邮箱/电话)。
- 实测状态:✅ 当前 **15 条**在公示申请(`allAppCount` 在 appTypes 里是 0,**该计数不可信**,以 `currentNotices.length` 为准)。
  - 测试地址:**PA2026/0344**——"Outbuilding (pergola) addition to an existing dwelling-group with a reduced building setback to the primary street boundary";assessmentCategory "Merit Assessment (permitted use with variation)";variations ["Setbacks"];DCA Darwin Division;**公示期 2026-10-02 至 2026-10-16**(`exhibition.startDate/finishDate`);zone LMR;Darwin Mid Suburbs Area Plan。
- **局限**:只覆盖「当前在公示」的申请;**历史 DA 与已决 DA 没有公开接口**(未找到);小型/豁免 DA 可能不公示。
- 判读注意:`documents` 里 "PLN Statement of Effect"、"PLN Dimensioned Plan" 等是申请文件。**浏览器侧同站点页面含 YouTube 内嵌**(`videoProps`),脚本抓取时别打开页面,直接取 JSON。

---

## 8. 道路车流量、铁路线、机场 ANEF

### 8a 车流量(AADT)——✅ 开放数据(表格,无坐标)
- 来源:data.nt.gov.au **Annual Traffic Report**(DIPL/Department of Infrastructure, Planning and Logistics;许可 Creative Commons Attribution),按年一个数据集,如 `annual-traffic-report-2023`(元数据修改 2024-08-27;已有 2019–2023)
  数据集页:https://data.nt.gov.au/dataset/annual-traffic-report-2023
  关键表:`Table 1.1 Urban Primary 10 Year AADT`(`.../1.1-urban_primary_10_year_aadt.xls`)、`Table 3.1 Urban Coverage 10 Year AADT`(`3.1-urban_coverage_10_year_aadt.xls`)、`1.2/3.2` MADT、`6.1/6.2` Site Class Data(车型分类)、`7.1` Bike Path Counters、`4B` Primary Last Surveyed。
  CKAN API 取最新下载链接:`curl -s "https://data.nt.gov.au/api/3/action/package_show?id=annual-traffic-report-2023"` → `result.resources[].url`。
- 解析:XLS 每个 sheet 一个 region(`A`=Alice Springs、`D`=Darwin、`K`=Katherine、`T`=Tennant Creek);每行 `Road Name / Location`、`ADT Station`(如 UDVDP002)、`Direction`(Inbound/Outbound)、`Units`、2014…2023 各年 AADT。
- 实测状态:✅ 下载+解析通过(Python `xlrd`)。**表里没有经纬度**,只能用路名/站点名人工匹配到地址所在道路。
  - Darwin 近邻道路(2023 AADT,**Inbound 方向**):Bagot Road(站 UDVDP002)**17,866**(Primary);Trower Road(UDVDP009)**13,353**;Dick Ward Drive(UDVDP005)**6,946**。Coverage 表:Bagot Road(UDVDC042)11,438;Trower Road(UDVDC038)11,203。
  - **测试地址所在的 Nightcliff Road 不在 Table 1.1/3.1 的 Darwin sheet 里**(无 AADT 记录)。
- 判读注意:Inbound/Outbound 是单向,双向要相加;Coverage 表为周期性抽样(`.0` 年份为空表示该年没测,数值带小数的是估算);站点位置要查 `4B Primary Last Surveyed`/年报 PDF。

### 8b 铁路
- Darwin 都会区**无城市铁路**(常识;**不是实测**);Adelaide–Darwin 货运线是 AustralAsia Railway,在 Berrimah/East Arm 一线(未实测)。未找到官方免费铁路线空间服务,❌/⚠️。

### 8c 机场 / ANEF
- NT 规划方案 overlay 里有 `LPA - Land in Proximity to Airports`(实测出现在 Coconut Grove 的 Lot 09742,107 Dick Ward Dr——**Darwin International Airport 附近**)。测试地址 `parcelOverlays []` → 未命中。
- ANEF 等值线本体:**无免费空间服务**;来自 Darwin International Airport Master Plan(联邦机场主计划 PDF,未取得)。状态:⚠️(overlay 可用于 DA 在审地块;一般地址需人工)。

---

## 9. 政策红利(与住宅增值潜力相关的现行政策)

**只认官方原文 + 日期。本辖区实测结果:找到「拟议」修订原文,未找到「已生效」确认。**

- 官方原文(来源 1:https://haveyoursay.nt.gov.au/proposed-planning-scheme-amendment ,Browser 取得,2026-10-03):"The Department of Lands, Planning and Environment is proposing changes to the NT Planning Scheme 2020 ... to better assist the development of group dwellings and multiple dwellings." 具体变更原文:
  - "reduces the minimum area of land required to establish a one bedroom dwelling in Zone LMR (Low-Medium Density Residential) from 300 square metres, which is the rate that applies for all dwelling sizes, to 150 square metres;"
  - "reduces the minimum number of car parking spaces required per dwelling, from two spaces for all dwelling sizes, to one space for one bedroom dwellings; and"
  - "provides further reductions to required car parking numbers ranging from 5% up to 50% for dwellings located close to public transport, commercial areas, and for social housing."
- 官方原文(来源 2:https://environment.nt.gov.au/news/2025/amendments-to-the-nt-planning-scheme-2020 ,**Published 28 August 2025**):"We're seeking your feedback on proposed changes to the NT Planning Scheme 2020." 公示至 **Friday 29 August(2025)**;并称 "part of a national agreement between states and territories to reach a shared target of 1.2 million new, well-located homes over 5 years from mid-2024"。
- **状态判断:提案公示已于 2025-08-29 结束;修订是否已生效、生效日、最终条文——未找到官方确认**(未取得 Planning Scheme Amendment 公告)。**不得写成「NT 已把 LMR 一居室最小地块降到 150 m²」**,只能写「提案阶段(2025-08 公示),待确认」。
- **测试地址相关性**:Lot 00567 是 LMR 区(Low-Medium Density Residential)——若该提案生效,理论上与 group/multiple dwelling 门槛相关;**但 lot 面积未取得,无法评估**。
- 人工入口:NTLIS planning scheme amendments(https://www.ntlis.nt.gov.au/,未取得具体页面)、NT Government Gazette(未实测)。

---

## 测试地址实测结果汇总表(80 Nightcliff Road, Rapid Creek NT 0810)

| 检查项 | 数据源 | 状态 | 测试地址返回值 |
|---|---|---|---|
| 地址→坐标 | NTG "Northern Territory Locator"(非文档化) | ✅ | 130.85216214, -12.38018897(PointAddress,score 100) |
| 地块(lot/面积/边界) | — | ❌/⚠️ | 仅 "Lot 00567 Town of Nightcliff"(来自 DA);无面积、无边界 |
| strata | — | ⚠️ | 未验证(DA 写 existing dwelling-group) |
| 分区 | Planning Notices JSON(仅在审 DA 地块)/ NT Atlas | ✅(窄)/⚠️(通用) | LMR Low-Medium Density Residential;Darwin Mid Suburbs Area Plan |
| Overlays | 同上 | ✅(窄) | 无(无 LPA、无 LSSS) |
| Heritage | — | ❌/⚠️ | 未找到免费源 |
| Storm surge | data.nt.gov.au 整包 shapefile | ✅(2100 情景) | 不在 2100/100yr、1000yr 范围;最近边缘约 487 m;阳性对照(130.864,-12.380)命中 |
| 内陆洪水 | — | ❌ | Nightcliff 无公开图 |
| 山火 | — | ❌ | 无 |
| 滑坡 / ASS / 海岸侵蚀 | — | ❌ | 无 |
| UCV | — | ❌ | 无公开逐地块;业主 portal/Valuation Services |
| DA | Planning Notices Online JSON | ✅(仅当前公示) | PA2026/0344,公示 2026-10-02~10-16,Merit Assessment(setbacks) |
| 车流量 | data.nt.gov.au Annual Traffic Report | ✅(表格,无坐标) | Nightcliff Rd 无记录;邻近 Bagot Rd 17,866 / Trower Rd 13,353 / Dick Ward Dr 6,946(2023 inbound) |
| 铁路 | — | ❌ | 无(Darwin 无城市铁路,常识) |
| ANEF | overlay LPA + Master Plan | ⚠️ | LPA 未命中;ANEF 需机场 Master Plan |
| 政策 | haveyoursay.nt.gov.au / environment.nt.gov.au | ⚠️ | 提案公示至 2025-08-29;生效未确认 |

## 未解决 / 存疑清单(NT)

1. **NT 地籍/分区/overlay 的通用点查接口缺失**——最大缺口。NT Atlas(IMF)可人工;若要自动化,需向 DLPE spatial services(Spatial data and information management)申请 WMS/WFS 或使用 NT Atlas 后台(ArcIMS 类,**未实测**)。
2. 测试地址的 **lot 面积、边界、strata 状态**未取得。
3. 测试地址选自在审 DA,**有选择偏差**;对没有 DA 的地址,Notices JSON 无法给 zone。
4. **storm surge 只有 2100 情景的 100/1000 年一遇**(10000 年与 HAT 在 .lyr 里有引用但 shp 缺失;当前气候基线未取得)。
5. **NT 法定 overlay 的完整清单**(含是否有 flood / bushfire overlay)未核实;本次只见到 LPA/LSSS/CNV/DHD。
6. **NT Locator** 为非文档化代理端点,可能失效;Nominatim 仅街道级且非官方。
7. **UCV**:2026 年 Darwin/Palmerston 重估计划原文被截断("City of Pa...");无公开逐地块接口。
8. **政策**:150 m² / 停车减免提案**生效状态未核实**。
9. **Heritage、Aboriginal sacred sites、内陆洪水、山火、ASS**:均未找到免费空间服务。
10. NT 站点对 curl 普遍 Cloudflare 403;自动化必须固定 UA 或走 Browser;有被限速/封禁风险,未测试速率限制。
11. 下载的 storm surge 整包(29 MB,DLPE 官方,来源 data.nt.gov.au)存放于本次会话 scratchpad 的 `w/ss`,仅用于点在面内检验。
