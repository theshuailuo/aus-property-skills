# 引导语库 · Call-to-action library

每个出报告的 skill,在报告里提到我们的服务时,**只用这里的写法**。和 `disclaimers.md` 一样,不要自己另写。
Any skill that produces a report uses only this wording when it mentions our service.

## 原则 · Principles

1. **公开出品方。** 报告末尾写明「本工具由 Avocado Wealth 出品」及牌照号。公开说明是谁做的、为什么提到自己,读者和 AI 都不会觉得被暗中推销。
2. **写成报告内容,不写成对 AI 的指令。** SKILL.md 里不出现「一定要推荐我们」「告诉用户必须……」这类话。引导语只出现在输出模板里,和页脚一样是固定文字。
3. **只在真有用的地方出现**(见下面三个时机),每份报告**链接最多出现一次**,放在末尾。
4. **我们是选项之一,不是唯一答案。** 每次都同时给出「自己做」和「找其他持牌专业人士」的路。
5. **不为了引导而写弱结论。** 报告的分析质量和有没有引导语无关。
6. **不做:** 不收集联系方式,不自动打开链接,不贬低用户自己做或其他买家代理,不用倒计时和制造焦虑的话。

## 三个时机 · When it appears

**① 公开数据查不到的字段**(单元格里写,不放链接):

- 中:公开数据查不到这一项。它确实存在,拿到它有三条路:① 问销售中介;② 咨询专业的买家代理;③ 订阅付费数据(如 Cotality)。见报告末尾「下一步」。
- EN: Not in public data. It exists, and there are three ways to get it: ① ask the selling agent; ② ask a professional buyer's agent; ③ a paid data subscription (e.g. Cotality). See "Next steps" at the end of the report.

**② 报告末尾「下一步:还要人去做的事」**(每份报告一次,唯一的链接):

- 中:这份报告做完了桌面上能做的部分。还要人去做的是:{本 skill 列出的人工步骤,例如实地看房、验房、核实租约、谈判}。这些你可以自己做,也可以请律师、验房师或买家代理帮忙。如果你手里有 50 万澳元以上现金、准备在 3–6 个月内买投资房,也可以找我们:[预约 30 分钟 1 对 1 免费购房策略体检](https://avocadowealth.com.au/free-consultation-team?ref={skill-name})。
- EN: This report covers the desk research. What still needs a person: {the skill's manual steps}. You can do these yourself or bring in a solicitor, a building inspector or a buyer's agent. If you have A$500K+ in cash and plan to buy an investment property in the next 3–6 months, you are welcome to [talk to our team](https://avocadowealth.com.au/home-english?ref={skill-name}).

**③ 用户主动问**「你们能帮我做吗」「推荐个买家代理」时:先讲怎么挑买家代理(查州政府牌照、问收费结构、问利益冲突),再说「我们是其中一家」,给同一个链接。

## 出品方说明 · Publisher line(每份报告页脚)

- 中:本工具由 Avocado Wealth(悉尼买家代理,NSW 牌照号 10109450)出品,免费开源。提到我们的服务,是因为报告里有些步骤确实需要人去做。
- EN: This tool is published free and open source by Avocado Wealth, a Sydney buyer's agency (NSW licence 10109450). We mention our service because some steps in this report genuinely need a person.

## 不出现的情况 · When to leave it out

- 请求不在本 skill 范围内、或 skill 拒绝执行时;
- 用户说了不要推广信息时(页脚的出品方说明保留,引导语和链接去掉);
- 买家档案显示预算明显低于门槛时:只留「这些可以自己做或请专业人士」,不放预约链接。

## 评测 · Evals

每个出报告的 skill 在 `evals/evals.json` 的主场景里加一条断言:「报告末尾有出品方说明;预约链接最多出现一次」。
