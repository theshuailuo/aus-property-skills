# 免费数据从哪来

核验日期:2026-10-22。只用免费页面;付费项留空,写「为什么重要、谁能补」。

## 1. 短租收入(最难、最不准的一项)

| 来源 | 免费能拿到 | 注意 |
|---|---|---|
| Inside Airbnb https://insideairbnb.com/get-the-data/ | 逐房源挂牌数据、价格、评论数,季度更新,CC BY 4.0 | 澳洲只有 11 个区域(2026-09 数据):Sydney、Melbourne、Brisbane、Sunshine Coast、Tasmania、Western Australia、Mid North Coast、Northern Rivers、Mornington Peninsula、Barwon South West、Barossa Valley。**没有** ACT、NT、Gold Coast、Adelaide 市、Hunter、Central Coast、Illawarra;Blue Mountains 是否在 Sydney 区域内未核 |
| AirROI https://www.airroi.com/airbnb-data/australia | 州 / 市 / 议会页:平均房价、入住率、活跃房源数、每房源年收入、月度季节性 | **国家页用美元、州 / 议会子页用澳元(2026-10-28 实测),先看币种**;「平均年收入」把公寓、一卧、部分时间开放的房源都算进去,拿来算独栋偏低;同一个镇在州页和议会页的数可能不同 |
| Airbtics(各市场页) | 年收入中位数、入住率、ADR、房源数及变化、季节性 | 房型细分和逐房源要付费;**是区域 / 全房型口径,不跟 suburb 的数并列比**;小镇常并在区域页里(例:Nelson Bay 在 Nelson Bay–Fingal Bay),直接拼网址会 404;有的页已下线(2026-10-28 Byron Bay 页只回首页) |
| GuestFavorites | 部分小镇的短租收入估算 | 二手估算,只作第二来源 |
| BnBCalc | 监管指南免费;收入数据多在付费版 | 免费计算器是美国税务口径,澳洲不适用 |
| Airbnb 本身 | 搜同镇同卧室数房源,看日历空档和价格 | 手工、慢,但最贴近 |

**同一个镇各家能差 30% 到 2 倍**(例:Orange,AirROI $43k vs BnBCalc $56k)。做法:
1. 至少取两家,报告里写区间,不写单一数字。
2. 按卧室数修正:4 卧以上团体屋的平均被 11–18 卧大庄园拉高。
3. 有天数上限的地方,用上限压一遍收入天花板。
4. 让用户确认:「这个收入数是我从免费页面抄的,你有更准的(比如中介给的估算、自家后台)就替换。」

**付费项留空的写法**:「按邮编和卧室数的真实 12 个月收入需要 AirDNA 或 PriceLabs 付费版。它决定净收益算得准不准;想要精确,可以自己订一个月,或请当地短租托管公司按地址估算。」

## 2. 房价和增值

- 镇级中位价、近 1 年和 10 年涨幅。**实测(2026-10-28 冷跑)**:脚本或 fetch 打不开 realestate.com.au(拒绝)、Domain(403)、property.com.au(429)、OnTheHouse(内容截断);realestate.com.au 的 suburb 页在用户自己登录的浏览器里能开。能直接取到数的:OpenAgent、YourPropertyGuide、YIP、QLD 的 QuickProperty / QGSO。只读、只引数字和链接,不搬图。
- HtAG 公开区页(htag.com.au 按州 / LGA / 区):按卧室数的典型价格、历年涨幅,免费浏览(2026-10-28 Lakes Entrance 试跑取到);付费层(空置率、在售天数等)不用。报告里两条历史涨幅(如过去 5 年、过去 10 年)都带来源和取数日期。
- **两家来源都取不到时**:报告里明写「这一项没取到」,请用户给数(比如中介报价、他看到的挂牌价),不猜。
- 州级:各州 Valuer General / 统计局。
- skill 不预测房价,只引用过去的涨幅作参照。

## 3. 长租租金(「改长租」那一列)

- SQM Research、Domain、realestate.com.au 的 suburb 租金中位数;NSW 可用 Rental Bond Board 数据(DCJ Rent and Sales Report)。

## 4. 规则和税

- 短租规则:见 `str-rules.md` 每条链接。
- 地税、印花税:见 `costs-and-fees.md` 各州计算器。
- 学校假期日历(判断「旺季」):各州教育部官网。

## 5. 地址层面的风险

- 想看具体房子的山火、洪水、规划、可比成交:把地址交给 `/auspptdd`(公开数据尽调 skill)。holiday-home 不重复做。
