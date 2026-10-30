# 交互报告(买入入口)· case.json 约定

核验日期:2026-10-28。来源:Lakes Entrance 试跑做出的交互页,匿名示例见 `examples/lakes-entrance.case.json` 和 `.html`。

## 1. 文件

| 文件 | 作用 |
|---|---|
| `templates/interactive/engine.js` | 算法:`holiday_calc.py` 买入模式的 JS 版,加七条路的比较 |
| `templates/interactive/report.js` `report.css` `template.html` | 页面:首页结论、七路对比、0–20 年时间曲线、「结论什么情况会反过来」、19 个带「?」说明的滑动条、瀑布图、自用排法、持平涨幅、净身家曲线。浅色和深色主题,手机能用,能打印 |
| `scripts/build_report.py` | `python scripts/build_report.py case.json report.html`,拼成一个独立 HTML,只用标准库 |
| `scripts/test_engine.js` | `node scripts/test_engine.js`:engine.js 和 holiday_calc.py 逐数一致,改了任何一边都要跑 |

目前只有中文。英文用户用 `holiday_calc.py --html` 的静态报告;英文版交互页要把 report.js 里的句子抽成语言包(待做)。

## 2. 持平涨幅:一把尺

脚本、engine.js、页面用同一个口径(2026-10-28 统一,0.5.0 起):

- 买房要掏的一次性现金(首付、印花税、家具杂费),在替代方案里按**该方案的税后回报率**滚(定期、指数基金、提前还自住房贷)。
- 每年要往里掏或省下的钱,**各条路一律按定期税后利率**计机会成本。

这样七条路排出来的先后在脚本和页面一致。之前的「两两对比」(每年的钱也按对方回报率滚)对指数基金和还房贷的持平涨幅更高(Lakes 示例:还房贷 8.9% 对 8.2%)。报告里不用解释两种口径,只说「每年掏的钱按定期税后利率算机会成本」。

## 3. case.json 每次要填的

- `today`(YYYY-MM-DD,算 2027-07-01 前还剩几年)、`pageTitle`、`eyebrow`、`title`、`subtitle`
- `defaults`:滑动条初值。键名:`price lvr rate rev0 mgmtFee peak off peakBlocked insurance otherHold mtr deposit index homeLoanRate ltRent bookNights bookNightly growth years vrltEscalate`
- `model`:`state`(NSW / VIC / QLD 用内置印花税表,其他州给 `dutyRate` 或 `duty`)、`vrlt`(只有 VIC 为 true)、`peakVal` / `offVal`(让一晚旺季 / 淡季给客人能多收多少)、`adr`、`platformFee`、`levy`、`directCosts`、`landTax`、`cpi`、`sellPct`、`otherCosts`、`furnishing`、`dwelling`、`optOwn{peak, off}`、`revRange`(可选,`[低, 高]`,全年房费,和 `rev0` 同口径;填了首页结论句带每年要掏的区间。只有一个收入来源时才不填)
- `growthRefs`:两条当地历史涨幅,带来源(如过去 5 年、过去 10 年);`growthButtons`:首页三个涨幅按钮
- `text`:11 条本地化句子:`growthHistory growthSource rev0Hint revRefs revBasis optDesc optShort redFlags[] useLead peakValNote useCallouts`
- `help`:可覆盖某个滑动条的「?」说明
- `sectionsBefore` / `sectionsAfter` / `sectionsEnd`:agent 写的叙述章节(房源和市场、短租规则、六道关、要人做的、附录),HTML
- `quotes`:`[[标题, 原文], ...]`,房源描述、网页原文一律放这里,按纯文本转义显示
- `topbar`:只给使用者自己用(回到会话的按钮);公开报告不填

## 4. 公开版规矩

- 匿名:不点名房源,只留链接;不放房源日历、逐日价格、评价;仓库里的示例不用真实个人参数(用示例值并写明);不放 `topbar`。
- 图片按 `shared/images-policy.md`:只放链接和缩略图。
- 页脚的免责声明和署名在 `template.html` 里,原文取自 `shared/disclaimers.md` 和 `shared/cta.md`;预约链接只按 cta.md 的条件放在 `sectionsEnd`,页脚不放。
- `build_report.py` 对 agent 写的 HTML 走白名单:保留排版、表格、`<details>` 和画图用的 SVG;去掉脚本、事件属性、style、iframe 和非 http(s) 链接。被去掉的标签不报错,所以外部原文必须走 `quotes`。

## 5. 出报告前核对

页面首屏的「每年要掏」「房价每年至少要涨」「ATO 区」要和 `holiday_calc.py` 同一组输入的结果一致;不一致先查输入(维州空置税:脚本要把它算进 `land_tax`,页面按自用晚数自动算)。
