# 费用和州税:从毛收入到净收益

核验日期:2026-10-22。标【一手】的是直接读过的官方页面;【二手】是商家 / 博客,只当行情参考。

## 1. 平台费

**Airbnb**【一手】https://www.airbnb.com.au/help/article/1857
- **单边费(single fee)**:全部从房东到手钱里扣,「Most hosts pay 15.5%」,其余一般 14–16%。
- **分摊费(split fee)**:房东约 3%,客人付订单小计的 14.1–16.5%。Airbnb 原话说正在把所有房东转到单边费;转了就不能转回。
- 用了物业管理软件(PMS)的房东强制单边费。
- **澳洲切换日期官方没写**。二手说法:PMS 房东 2025-10-27;其余房东 2026-09-15(Hometime、Smoobu、Hostfully);Houst 说 2025-12,自相矛盾。**以房东后台显示为准。**
- **GST 是否包含在 15.5% 里没有官方说法**,二手三家互相矛盾(Houst 说已含;Hometime 说不含;MyAirHost 说加 GST 约 17.05%)。

**为什么 15.5% 这么要紧**:各家数据网站统计的「年收入」通常是客人付的总价。分摊费时代房东只被扣 3%;单边费时代是 15.5%。同样的「年收入」,房东到手少了约 12.5 个百分点。房东可以提价消化一部分,但只要用客人总价算收益率,就要按 15.5% 扣。

**Stayz / Vrbo**【一手,但页面自相矛盾】https://help.vrbo.com/articles/How-is-the-booking-fee-calculated:按单佣金 12%,Professional Plan 在澳洲最高 15%,另加 GST;同页又写 GST「always 0.5%」。二手说法 5–15% 不等。
**Booking.com**:官方没有公开澳洲费率;二手 10–25%,以签的 Accommodation Agreement 为准。

脚本参数:`platform_fee`,默认 0.155;用户在分摊费上、或主要走别的平台时改。

## 2. 托管

| 来源【二手】 | 地区 | 费率 |
|---|---|---|
| The Holidays Collection | Jervis Bay | 只管订单 13.2–15%;标准 15–16.5%;全托管 20%(含 GST) |
| Professional Holiday Homes | South Coast、Jervis Bay、Sydney | 18% 含 GST;新业主开通费 $1,995 |
| Compounding Property Group | Sydney | 15–30% |
| Boostly(英国)/ Airbnb 社区帖 | — | co-host 10–25%,轶事 |

- NSW 区域 co-host 费率**没有可靠来源**;skill 默认三档:自己管 0%、co-host 10%、全托管 20%。
- 要问清:按毛收入还是扣完平台费后算、含不含 GST、清洁和布草谁出。脚本按「扣完平台费后的收入」算托管费。

## 3. 持有成本(默认值,用户能改)

| 项 | 默认 / 年 | 说明 |
|---|---|---|
| 短租保险 | $5,000 | 普通房屋险可能不保短租;山火、洪水区更贵。要书面确认保单覆盖短租、山火(含飞火、烟熏)、洪水 |
| 市政费 + 水费 | $3,500 | 以议会账单为准;QLD 一些议会对短租收不同费率(见 str-rules.md) |
| 维修 + 家具更换 | 房价约 1% | 二手来源说 2–3%,默认取低值 |
| 水电网、日用品 | $5,000 | 太阳能能省一部分 |
| 清洁(大部分转嫁客人后的净额) | $3,000 | 直接费用,TR 2026/1 下仍可扣 |

## 4. 州税

| 州 | 印花税计算器【一手】 | 地税【一手】 | 度假屋要注意 |
|---|---|---|---|
| NSW | https://www.apps09.revenue.nsw.gov.au/erevenue/calculators/duties.php | 起征点土地价值 $1,075,000(2024 起冻结),超出部分 1.6% + $100;所有非自住地合并算 https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/land-tax/understanding-land-tax/thresholds-and-rates | 度假屋不符合主要居所豁免(要求作为住所使用、无其它用途;页面没直接写 holiday home,属推断) |
| VIC | https://www.sro.vic.gov.au/buying-property/land-transfer-stamp-duty/land-transfer-stamp-duty-calculator | 应税土地价值 $50,000 以下为零,往上分档 https://www.sro.vic.gov.au/about-us/rates-and-statistics/current-rates/land-tax-current-rates | **空置住宅地税(VRLT)全州适用**:上一年没人住满 6 个月就算空置,只挂牌出租不算。度假屋豁免要你或亲属每个日历年自己用至少 4 周,一人一年一套,建议记使用日志 https://www.sro.vic.gov.au/owning-property/vacant-residential-land-tax/exemptions-vacant-residential-land-tax 。短租税 7.5% 见 str-rules.md |
| QLD | https://qro.qld.gov.au/duties/transfer-duty/calculate/transfer-duty-estimator/ | 个人应税价值 $600,000 起征 https://qro.qld.gov.au/land-tax/calculate/individual/ (页面 2024-07 更新,2026-27 是否变动未核) | 主要居所豁免要求是你住的家,度假屋不符合(推断) |
| 其它州 | 让用户在州税务局计算器算 | 同左 | — |

外国买家附加印花税和附加地税:只给链接,skill 不算。

**VIC 的一个夹缝**:靠出租为主的度假屋,自用可能不到 4 周,拿不到 VRLT 度假屋豁免;一年住客又不满 6 个月的话,会被算空置。这跟 TR 2026/1「自用越少越好」方向相反。两者怎么同时满足,SRO 没有明说,让用户找税务师。

## 5. 印花税

脚本内置三州一般税率(不含首置、外国买家附加),2026-10-23 核过官方原表:
- NSW 2026/27(每年 7 月 1 日按 CPI 调整):https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/transfer-duty/rates
- VIC 非自住(2026-09-29 更新):https://www.sro.vic.gov.au/about-us/rates-and-statistics/current-rates/land-transfer-duty-non-principal-place-residence-current-rates
- QLD 一般税率(2026-06-25 更新):https://qro.qld.gov.au/duties/transfer-duty/calculate/rates/
其它州用户没给就按房价 4% 粗估,报告里标「请用州税务局计算器替换」。NSW 高价住宅的 premium duty 脚本没算。
