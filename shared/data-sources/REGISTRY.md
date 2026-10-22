# 数据源登记 · Data source registry

每个 skill 用到的外部数据源都登记在这里。新增来源先登记再用。
Every external data source a skill uses is registered here before use.

字段说明:**免费/付费**(免费 = 无需登录或订阅);**访问方式**(网页 / API / 下载包 / 只能用户自己的浏览器);**条款要点**(能不能自动取、能不能放进报告);**最后核验**(有人实际打开并取到数的日期)。没核过写「待核」,不猜。

| 来源 | 州 | 用途 | 免费/付费 | 访问方式 | 条款要点 | 最后核验 | 用到的 skill |
|---|---|---|---|---|---|---|---|
| NSW Valuer General(地价、成交记录包) | NSW | 地价史、历史成交 | 免费 | 网页 + 下载包 | 待核 | 待核 | auspptdd(待迁入) |
| NSW Planning Portal 空间查看器 | NSW | zone / FSR / 限高 / 最小地块 / heritage | 免费 | 网页 + 图层服务 | 待核 | 待核 | auspptdd(待迁入) |
| NSW 环境与遗产图层(mapprod3.environment.nsw.gov.au) | NSW | 洪水、山火等灾害图层 | 免费 | 图层服务 | 待核 | 待核 | auspptdd(待迁入) |
| BOCSAR | NSW | 犯罪统计 | 免费 | 网页 / 下载 | 待核 | 待核 | auspptdd(待迁入) |
| ABS 普查(data.api.abs.gov.au) | 全国 | 公屋、租住比、人口 | 免费 | API | 待核 | 待核 | auspptdd(待迁入) |
| SQM Research 免费页 | 全国(postcode 口径) | 空置率、在售库存、要价、租金 | 免费 | 网页(数据嵌在源码) | 待核(商业使用条款) | 待核 | auspptdd(待迁入) |
| VIC Planning 地图(planning.vic.gov.au / mapshare) | VIC | 规划与覆盖层 | 免费 | 网页 + 图层服务 | 待核 | 待核 | auspptdd(待迁入) |
| QLD 空间数据(spatial-gis.information.qld.gov.au) | QLD | 规划、灾害 | 免费 | 图层服务 | 待核 | 待核 | auspptdd(待迁入) |
| SA SAPPA(sappa.plan.sa.gov.au) | SA | 规划与地块 | 免费 | 网页 + 接口 | 待核 | 待核 | auspptdd(待迁入) |
| WA SLIP / Landgate | WA | 规划、地块 | 免费 | 图层服务 | 待核 | 待核 | auspptdd(待迁入) |
| TAS theLIST | TAS | 规划、地块、灾害 | 免费 | 图层服务 | 待核 | 待核 | auspptdd(待迁入) |
| NT NTLIS | NT | 地块、规划 | 免费 | 网页 + 图层服务 | 待核 | 待核 | auspptdd(待迁入) |
| ACT Revenue | ACT | 税费、地价 | 免费 | 网页 | 待核 | 待核 | auspptdd(待迁入) |
| realestate.com.au / domain.com.au | 全国 | 挂牌信息、照片 | 免费浏览 | **只能用户自己的浏览器**;脚本访问被拦 | 照片只放链接 + 小图,见 `../images-policy.md` | 待核 | auspptdd(待迁入) |

> 以上首批来源取自 auspptdd 当前版本的说明文件;auspptdd 迁入时由尽调线逐条核验并填「条款要点」与「最后核验」。
> The first rows come from the current auspptdd notes; terms and verification dates will be filled in when auspptdd migrates.

## 付费数据(本仓库不用,只记录「为什么重要、谁能补」)

| 来源 | 为什么重要 | 谁能补 |
|---|---|---|
| Cotality(原 CoreLogic)/ RP Data | 逐次调价史、AVM、完整可比 | 有订阅的买家代理、中介、贷款经纪 |
| HtAG 付费层 | 空置率与在售天数(2026-10 起已锁进付费层) | HtAG 订阅用户 |
