# Versions · 版本

更新方法:看下表,本机 skill 版本比表里低就重新安装(见 README「安装」)。skill 不会在会话里自动检查更新。
To update: compare with the table below and reinstall any skill that is behind (see README). Skills never check for updates on their own.

| Skill | Version | Last Updated |
|---|---|---|
| auspptdd | 0.4.0 | 2026-10-28 |

<!-- 每发布一个 skill 加一行,例如 | holiday-home | 0.1.0 | 2026-11-01 | -->

---

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
