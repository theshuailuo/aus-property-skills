# 州适配通用思路(遇到没有州说明文件、或州说明里的接口失效时照此做)

## 每个州都要回答的九个问题
1. 地址 → 坐标 → 地块(lot/plan、面积、边界);plan 前缀怎么看出是不是 strata。
2. 规划分区与全部 overlay(含 heritage)在哪查;法规条文全文在哪拿。
3. 洪水:规划 overlay 之外有没有独立的官方洪水范围图。
4. 山火:bushfire prone area 图层。
5. 滑坡、酸性硫酸盐土、采矿沉降、污染场地。
6. 官方逐地块估价有没有免费公开查询(很多州没有,没有就写没有)。
7. DA / 规划许可活动有没有公开接口。
8. 道路等级与车流量(AADT)、铁路、机场 ANEF。
9. 与增值潜力相关的现行州政策及其资格排除项(只认官方原文,带生效日期)。

NSW 的完整写法见 `state-NSW.md`;其它州见 `state-<STATE>.md`。

## 找源的顺序
1. 该州开放数据门户(data.<州>.gov.au 的 CKAN 搜索 API)搜数据集名,拿到 ArcGIS REST 或 WFS 地址。
2. 该州官方地图站(VicPlan、Queensland Globe、PlanWA、SAPPA、LISTmap、ACTmapi、NT Atlas)用浏览器开一次,从网络请求里读它背后调的服务地址。
3. Council 自己的 open data / interactive mapping(QLD 这类规划归 council 的州必走)。
4. 三条路都不通 → 写「免费数据不覆盖 · 下一步:浏览器人工看 <入口 URL>(谁做)」,列进报告第 8 节「要人做」。

## 通用点查写法
- ArcGIS REST:`<服务>/<图层号>/query?f=json&geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false`
  - 最近距离:加 `distance=<米>&units=esriSRUnit_Meter&returnGeometry=true&outSR=4326`,客户端算点到多边形边的最小距离。
  - 有些图层对点查返回空、只接受属性查询(NSW 的估价点图层就是),先 `where=1=1&resultRecordCount=1` 看字段,再按属性查。
  - 有些服务对 `where` + 几何同用、或自定义 `outFields` 会 400:退回 `outFields=*` + 几何,客户端过滤。
- WFS:`<服务>?service=WFS&version=2.0.0&request=GetFeature&typeNames=<图层>&outputFormat=application/json&cql_filter=INTERSECTS(<几何字段>,POINT({lat} {lon}))`(坐标轴顺序各服务不同,返回 0 条时先对调再判无)
- 返回 0 条只有在「图层覆盖该 LGA 且阳性对照能命中」时才写「未检出 · 目前看风险较低」;图层不覆盖该 LGA 就写「未覆盖」。阳性点取最近水体岸线 50 m 内,阴性点取最近高地。

## 法规全文被挡时
州法规网站(NSW legislation、VIC legislation 等)常对脚本 403、对浏览器弹 Cloudflare 人机页。统一绕法:`https://web.archive.org/web/2id_/<原 URL>` 取原样快照(`id_` 后缀 = 不加存档包装);返回体可能是 gzip(前两字节 `1f 8b`)要先解压;报告注明「条文为存档快照(日期),出价前律师按现行版复核」。没有快照 → 进「要人做」。

## 道路与 OSM
- 路网优先用该州官方 Transport / Roads 图层(NSW:Transport Theme RoadSegment,带道路等级字段);OSM Overpass 的公共镜像经常整批不可用,只作备选。
- 步行距离用 OSRM 公共步行路由(`routing.openstreetmap.de/routed-foot`),不用直线。
- 车流量(AADT)各州都是交互地图,没有稳定接口:一律写进「要人做」并给入口 URL。

## 纪律
- 图层号、字段名以当场实测为准,州说明里写的只是上次测通的值。
- 接口变了:修好后回写该州说明文件,末尾记一行日期与改了什么。
- 全国通用、不用换州的:ArcGIS geocoder、OSRM 步行路由、ABS Data API 与 ASGS 图层、SQM Research 免费页、Aussie / OnTheHouse 物业页(Cotality 数据)、web.archive.org;REA / Domain 要用用户自己的浏览器(对脚本有防爬,见 SKILL.md)。
- 时间:任何单步预计超过 5 分钟(逐年成交循环、Aussie 限速抓取、BOCSAR 下载)都后台跑,期间做别的步。
- Windows:所有脚本开头 `sys.stdout.reconfigure(encoding='utf-8')`,所有 `open()` 带 `encoding='utf-8'`;或设环境变量 `PYTHONUTF8=1`。
