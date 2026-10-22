# 图片口径 · Images policy

## 公开版(本仓库里的 skill 默认行为)

- 房源照片:**只放房源链接 + 小图(缩略图)**,用来识别是哪套房。不下载、不转存、不放大图。
- 翻新前后对比图:公开版不做。
- 街景:只放链接,不截图。
- 地图、规划图层、官方图表:可以放,注明来源(各来源条款见 `data-sources/REGISTRY.md`)。
- 每份报告带 `disclaimers.md`「图片」一句。

## 自用版(private overlay)

如果某个 skill 目录下存在 `private.local.md`(被 `.gitignore` 忽略,只在使用者本机),skill 先读它,它可以打开公开版关掉的功能(例如使用者本人内部使用的大图、前后对比)。这个文件**永远不提交**;校验脚本发现它被 git 跟踪会直接报错。

## 为什么这样定

- realestate.com.au(REA)2024-12 起诉 Domain,指其抓取并使用 REA 独家房源的照片与户型图;2025-07 报道双方和解,条款未公开。照片版权通常属于摄影师或中介,房源网站有自己的使用条款(例如 Domain 使用条款禁止抓取图片、禁止建房产信息数据库)。
- 公开、可下载的报告里放大图,风险落在发布者身上;链接 + 小图足够识别房源。

## 收到投诉怎么办

改 skill(收紧对应来源的用法)并在 `VERSIONS.md` 记一行;不下架整个仓库。

---

**EN summary**: Public skills show listing links and thumbnails only — no downloaded or full-size listing photos, no before/after comparisons, no street-view screenshots. Maps and official layers are fine with attribution. A local, git-ignored `private.local.md` may enable more for the owner's own use and must never be committed. Background: REA sued Domain in Dec 2024 over scraped listing photos and floor plans; a settlement was reported in July 2025 (terms not public). On a complaint we change the skill rather than take the repo down.
