# 报告模板 · Report template

这里将放全仓共用的中英 HTML 报告模板。

- **正本 = auspptdd 的报告版式**(`skills/auspptdd/templates/report.html` + `scripts/gen_report.py`)。它已经过两轮独立屋、两轮公寓冷跑验证;抽成共用模板时整体搬过来,避免出现两份版式各自漂移。
- **例外:holiday-home 用自己的交互版**(`skills/holiday-home/templates/interactive/`,带滑动条的计算器页,和尽调文件不是一类),不跟 auspptdd 版式合并。免责声明和署名两边都照 `shared/disclaimers.md`、`shared/cta.md` 原文。
- 在那之前,新 skill 先用纯 Markdown 输出,结构按:结论 → 关键事实(带来源与取数日期)→ 风险 → 要人做的事 → 免责。

---

This folder will hold the shared bilingual HTML report template. The source of truth is the auspptdd report layout (`skills/auspptdd/templates/report.html` + `scripts/gen_report.py`), already verified in four cold runs; it will be moved here as one piece. Exception: holiday-home keeps its own interactive calculator page (`skills/holiday-home/templates/interactive/`) and is not merged into the auspptdd layout; both use the shared disclaimer and attribution text verbatim. Until then, new skills output Markdown in this order: conclusion → key facts (with source and retrieval date) → risks → what still needs a person → disclaimer.
