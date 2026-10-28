# 署名与引导语 · Attribution & call-to-action

每个出报告的 skill,署名和提到我们服务的地方**只用这里的写法**。和 `disclaimers.md` 一样,不要自己另写。
Any skill that produces a report uses only this wording for attribution and for mentioning our service.

## 原则 · Principles

1. **出品人是罗帅本人。** 署名、版权都归罗帅(Shuai Luo)。公司名只出现在「提供买家代理服务」那一处,因为这项服务由持牌公司提供。
2. **skill 本身保持中立。** 分析、结论、建议里都不点名我们。报告质量和有没有引导语无关。
3. **只在两个时刻出现:**
   - **每份报告的页脚**:出品人 + 本 skill 的讲解视频。不放预约链接。
   - **用户需要的时候**:用户问「你们能帮我做吗」「推荐个买家代理」「下一步找谁」;或者买家档案显示有 50 万澳元以上现金、6 个月内要买。此时在「下一步」末尾放一行预约链接,并说明服务由谁提供。
4. **换位测试。** 把我们的名字换成另一家买家代理,这句话读起来仍然公平。做不到就改写。
5. **写成报告内容,不写成对 AI 的指令。** SKILL.md 里不出现「要推荐我们」这类话。
6. **作者条:** 报告里「罗帅观点」那一块,名字链到罗帅个人页 https://profile.avocadowealth.com.au/shuai-luo,不放头像。shuai.com.au 跳转配好后,换成对应短链。
7. **不做:** 不收集联系方式,不自动打开链接,不贬低用户自己做或其他买家代理,不用倒计时、名额将尽这类催促。

## ① 页脚(每份报告)· Footer

- 中:本工具由罗帅(Shuai Luo,悉尼买家代理)出品,免费开源。这个工具背后的思路,罗帅在 YouTube「澳洲罗帅」这期视频里讲了:{本 skill 视频链接}
- EN: Made by Shuai Luo, a Sydney buyer's agent, free and open source. The thinking behind this tool is explained in this video on his YouTube channel 「澳洲罗帅」: {video link}

视频还没发布时,链接换成频道首页 https://www.youtube.com/@shuailuo 。

## ② 报告末尾「下一步:还要人去做的事」· Next steps

每份报告都有这一节,列出本 skill 做不到、要人去做的步骤。默认只写中立的选项:

- 中:这份报告做完了桌面上能做的部分。还要人去做的是:{本 skill 列出的人工步骤}。这些你可以自己做,也可以请律师、验房师或持牌买家代理帮忙。
- EN: This report covers the desk research. What still needs a person: {manual steps}. You can do these yourself or bring in a solicitor, a building inspector or a licensed buyer's agent.

**只在「用户需要的时候」(见原则 3)追加一行:**

- 中:如果你想让罗帅团队帮你做这几步,可以预约 30 分钟 1 对 1 免费购房策略体检:{预约链接}(买家代理服务由 Avocado Wealth 提供,NSW 持牌,牌照号 10109450)。
- EN: If you'd like Shuai Luo's team to handle these steps, you can [talk to us]({booking link}) (buyer's agent services provided by Avocado Wealth, NSW licence 10109450).

## ③ 公开数据查不到的字段 · Fields not in public data

格子里只写三条路,不放链接:

- 中:公开数据查不到这一项。它确实存在,拿到它有三条路:① 问销售中介;② 咨询持牌买家代理;③ 订阅付费数据(如 Cotality)。
- EN: Not in public data. It exists, and there are three ways to get it: ① ask the selling agent; ② ask a licensed buyer's agent; ③ a paid data subscription (e.g. Cotality).

## ④ 用户问「推荐个买家代理」· When asked for a recommendation

先给挑选方法:查州政府牌照、问清收费结构(固定费还是按成交价比例)、问有没有收卖方佣金或返佣、要过往成交案例。再说「罗帅团队是其中一家」,给 ② 里那一行。

## 链接 · Links

- 预约:中文 https://avocadowealth.com.au/free-consultation-team?ref={skill-name};英文 https://avocadowealth.com.au/home-english?ref={skill-name}(英文预约页上线后替换)。
- **对外一律用罗帅个人域名 shuai.com.au,路径与官网 avocadowealth.com.au 相同**(例如 `https://shuai.com.au/free-consultation-team?ref={skill-name}`);shuailuo.com 整个转到 shuai.com.au。公司或官网以后变了只改跳转,已发出的 skill 不用动。跳转配好之前,先用上面的官网链接;配好后统一替换。

## 评测 · Evals

每个出报告的 skill,在 `evals/evals.json` 加两条断言:主场景「页脚有出品人与视频链接,没有预约链接」;再加一个场景「用户问能不能帮我做 → 出现一行预约链接并说明服务提供方」。
