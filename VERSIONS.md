# Versions · 版本

更新方法:看下表,本机 skill 版本比表里低就重新安装(见 README「安装」)。skill 不会在会话里自动检查更新。
To update: compare with the table below and reinstall any skill that is behind (see README). Skills never check for updates on their own.

| Skill | Version | Last Updated |
|---|---|---|
| holiday-home | 0.5.1 | 2026-10-28 |
| auspptdd | 0.4.3 | 2026-10-28 |

<!-- 每发布一个 skill 加一行,例如 | holiday-home | 0.1.0 | 2026-11-01 | -->

---

### 0.3.2 (2026-10-28)
- `auspptdd` 0.4.3(Leichhardt 独立屋冷跑 Run 5 回写):① 开跑前门卫 `scripts/browser_gate.py`——会话浏览器站点未放行就整条走无浏览器路径,流水线不再挂在一个弹窗上;REA 链接拒开立刻向人要地址;② 报告:顶栏真正悬浮(overflow clip)、亮/暗切换、土地区三行两列(地块图|剖面、文字|地价折线、官方航拍+地籍|同街散点)、同街成交表只展开 3 行、首图规矩(本次挂牌封面在前、翻新前照片在后)、可比地图瓦片链 NSW 底图→Esri→OSM(本地打开不再 Access blocked);③ `dom.no_guide` 让拍卖无指引的挂牌价阶梯图在 `--check` 记为不适用;④ state-NSW.md 加 Inner West 行(council 2017 洪水 PDF 图集结构)。
- `auspptdd` 0.4.3 (Leichhardt house cold run 5): a pre-run browser gate so the pipeline never waits on a site prompt (REA links: ask for the address at once); sticky top bar with a light/dark toggle; land section in two-column rows with the official NSW aerial photo and lot ring, land-value line, three-row street table; cover-photo-first rule; map tile chain NSW base map → Esri → OSM; `dom.no_guide` for auctions; Inner West flood PDF notes.

### 0.3.1 (2026-10-28)
- `holiday-home` 0.5.1:「罗帅观点」的免责句挪到这一节开头;作者栏不放照片,链到个人主页;`shared/report-template` 写明 holiday-home 用自己的交互版。
- `holiday-home` 0.5.1: the disclaimer for Luo Shuai's view now opens that section; the author strip links his personal page instead of a photo; report-template README notes holiday-home keeps its interactive layout.

### 0.3.0 (2026-10-28)
- 新 skill `holiday-home` v0.5.0:澳洲度假屋「买还是订 / 留还是卖」。三个触发场景入口(看到当地房价、看中某套、住了某个 Airbnb),先在对话里给速览、每轮最多问 3 个问题;各州与市政短租规则;ATO TR 2026/1 + PCG 2026/3 自用日历粗筛(绿 / 黄 / 红);Airbnb 房东单边费约 15.5%、托管、持有成本、土地税后的净收益;和订房、定期、指数基金、提前还房贷、当地长租房比的持平涨幅(一把尺:每年掏的钱按定期税后利率计机会成本);2026 负扣税与 CGT 改革的「已有」入口;六道关自检。中文买入入口出交互报告(滑动条、七路对比、ATO 区随日历变),附匿名示例 `examples/lakes-entrance.html`。评测 10 例(含注入、超范围、一句话速览)。
- 数据源登记表新增 holiday-home 12 行。
- New skill `holiday-home` 0.5.0: buy or book / keep or sell for Australian holiday homes — short-stay rules by state and council, TR 2026/1 own-use screen, net yield after the ~15.5% host fee, breakeven growth against booking, deposit, index fund, paying down the home loan and a long-term rental (one yardstick), the 2026 reform for owners, six-gate self-check; interactive report for the Chinese buy entry with an anonymised example; 10 evals.

### 0.2.2 (2026-10-28)
- `auspptdd` 0.4.2:并入本机副本上先行做出的四条(价格标尺拆层、剖面图永远画、可比自动链档案页、Leaflet 真地图含地块边界)与「标准图件登记表」`FIGURES` + `--check`(跑前核对缺哪张图、缺哪个字段;登记表区分 house / unit 路径,并收录 0.4.1 新图)。至此仓库与本机副本重新一致。
- `auspptdd` 0.4.2: merges the four changes made earlier on the local copy (layered price ruler, profile always drawn, clickable comparables, Leaflet map with lot boundary) and the `FIGURES` registry with `--check`; repository and local copy are back in step.

### 0.2.1 (2026-10-28)
- `auspptdd` 0.4.1:读报告后的第二轮版式与口径修正——总览只留身份信息、来源核对收成英雄面板下的一行、时间线点上标价并按事件类型分形、首次出价改为可选(拍卖不给,给不出理由就写「待与中介沟通后定」)、区间措辞改「基于已核实信息的判断范围」、所有自画图加图例与防重叠、unit 路径第 4 节改楼栋两张图与楼内全部成交表、同楼可比省略地图并给 Google 地图兜底、第 2/5 节加 AI 生成提示、月供按 LVR 算并修正利率单位(小数,填 6.15 会被纠正为 0.0615)。
- `auspptdd` 0.4.1: second-pass layout and wording fixes after reading the reports — overview deduplicated against the hero panel, source chips, priced timeline, optional first offer, range wording, chart legends and label dodging, building charts and building-sales table for units, map fallback, AI note on sections 2 and 5, repayments on LVR with the rate-unit bug fixed.

### 0.2.0 (2026-10-28)
- 新 skill `auspptdd` v0.4.0:澳洲住宅尽调公开数据版,独立屋与 strata 公寓两条路径;NSW、WA 各冷跑过独立屋与公寓(Beacon Hill、Salamander Bay、East Perth、North Sydney)。
- 报告署名与引导语按 `shared/cta.md`(页脚出品人 + 视频;预约行只在用户要求时出现);免责按 `shared/disclaimers.md`;付费口径不带链接。
- 数据源登记表:auspptdd 的 26 行改为实际核验日期;新增 Domain 楼栋页、OnTheHouse、Allhomes、Landgate SLIP 等。
- New skill `auspptdd` 0.4.0: residential due diligence on free public data, house and strata-unit paths, cold-run in NSW and WA; attribution and disclaimers now follow the shared wording; data-source registry filled in.

### 0.1.0 (2026-10-22)
- 仓库脚手架:README 中英、AGENTS.md、MIT + 品牌说明、ROADMAP(57 个 skill)、共享免责/图片/数据源、skill 写法样板、校验脚本。
- 对外链接规则:个人域名 shuai.com.au,路径同官网(跳转配好后替换)。
- shared/cta.md:署名改为罗帅本人(公司只在提供服务处出现);skill 内保持中立,预约链接只在用户需要时出现;参照 Corey 的换位测试。
- ROADMAP 分两部分:SPEAR 买房五步(38)+ 买后持有·增值·退出(19);A 加「谈判」;第一批改选区优先;中文 CTA 改写。
- README 流程图与 ROADMAP 改按 SPEAR 五步;英文 CTA 改 A$500K–1M 并指向英文官网;YouTube 链接补齐;TRADEMARK 扩充名称清单。
- 结构规则:auspptdd 为总装 skill,9 个深挖模块可单独使用,同一逻辑只有一个正本(AGENTS.md §3.1、ROADMAP 🧩)。
- Repository scaffold: bilingual README, AGENTS.md, MIT + trademark notice, 57-skill roadmap, shared disclaimers / images policy / data-source registry, skill template, validation script.
