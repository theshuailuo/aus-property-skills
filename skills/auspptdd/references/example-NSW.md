# Worked example:112A Salamander Way, Salamander Bay NSW 2317(Port Stephens LGA)· 冷跑 Run 2,2026-10-22/23

这是 v0.2 → v0.3 之间用「只知道地址」的条件跑出来的一套房,所有数字来自免费公开源,方法在 `state-NSW.md` / `free-sources-NSW.md`。`templates/data.example.json` + `templates/example/*.svg` 就是这套房的完整 data.json,可直接渲染看版式。数字只用于对照方法是否跑通,下一套房一律重查。

## 事实(主源 Aussie / Cotality,交叉核对 Domain)
| 项 | 值 | 来源 |
|---|---|---|
| 地块 | Lot 1081 DP 1188746,Torrens;2013 年从 112 号分出(相邻 Lot 1082 = 112 号 1,122 m²) | NSW_Cadastre L9 |
| 面积 / 地价 | 908 m²;VG $632,000 @ 2025-07-01($696/m²);2021 $441k → 2022 $606k → 2023 $602k → 2024 $602k → 2025 $632k | SIXV L5(propid 3724584,按 propid 查) |
| 分区 | C4 Environmental Living,Port Stephens LEP 2013;最小地块 1 ha(cl 4.1);限高 9 m;无 FSR 图 | EPI L2/L4/L5 |
| 房型 | 5 卧 2 卫 2 车,单层,230 m² 建筑,2000 年建 | Aussie 物业页;Domain 同 |
| 挂牌 | $1,350,000,2026-06-04 上架(Domain);Aussie 首挂 2026-06;PRD Port Stephens | Domain 挂牌页 + 物业档案页 |
| 历史成交 | 2019-02-11 $785,000(VG last sale;Domain 131 天在市);2015-02 $680,000(21 天);Aussie 另显示「Sold Jun 2021」但 VG/Domain 均无 → 进「要问中介」 | SIXV L1;Domain;Aussie |
| Domain 免费估值 | $1.19M – $1.38M – $1.57M「高置信」;租金估 $995/周 | Domain property-profile |
| 照片 | Domain 挂牌页 26 张,原始签名 URL 热链(改尺寸路径即 400);REA / property.com.au `curl` 429 | Domain |

## 风险(council 层从 ArcGIS Online 反查,见 state-NSW.md §3 第二条路)
| 项 | 结果 | 来源 |
|---|---|---|
| 洪水 | **条件项**:Port Stephens「Flood Planning Area 2023」Overland Flow 类别命中;主流 FPA 多边形 124 m 外;阳性对照 Salamander Bay 岸边、阴性对照 Nelson Bay 高地均符合;「Flood Prone Land 2023」是 192 km² 近乎全覆盖层,只作旁注 | services-ap1 FeatureServer(Flood_Planning_Area_/2、Flood_Prone_Land/170) |
| 山火 | RFS BFPL Vegetation Buffer 命中;Cat 1 斑块 57 m(3,821 m²)、Cat 2 106 m;council 2021 版点未命中、Buffer 25 m | Fire/BFPL L0;council Bushfire_Prone_Land/161 |
| 滑坡 | 州 Hazard L2 与 council 均不覆盖 Port Stephens → 未覆盖;实测地势 6 m AHD、落差 0 | HAZ L2 distinct LGA_NAME 只 6 个 |
| ANEF | 州 Protection L2 不覆盖本 LGA(Williamtown 阳性对照返回空);council ANEF 2025 层 5 km 内无等值线(Williamtown 阳性对照 40+) | council ANEF_2025/175 |
| 酸性硫酸盐土 | Class 4(LEP cl 7.1:2 m 以下工程要 consent + ASS 计划) | PRO L1 |
| 雨水控制区 | council Drainage Control Areas 命中 Stormwater Control Area | council Drainage___Control_Areas/3 |
| 主干道 | 临 Salamander Way(functionhierarchy 4),地块最近边距路中线 21.7 m | TRANS L5 |
| 公屋 | SAL 3.2%(69/2,159);SA2 Nelson Bay Peninsula 2.2%(205/9,176) | ABS C21_G37 |
| 犯罪 | 2025-07 至 2026-06 331 起,68.6/千人 vs 全州 72.9(比值 0.94;人口 SAL 4,824、NSW 8,670,105 ABS ERP_Q 2026-Q1) | BOCSAR SuburbData.zip |
| 条文 | LEP 快照 2026-08-01(epi-2013-0755):C4 用途表含 Dual occupancies、Dwelling houses,无 secondary dwellings;cl 4.1B 无 C4 行;cl 7.15 只管 RU1/RU2/C2/C3。Housing SEPP 快照 2025-09-17:s 49–50 只列 R1–R5,s 164(1)(a)(g)(xvi) 排除 bushfire prone 与 Port Stephens flood planning 地 | web.archive.org id_ |

## 市场与可比
- 官方成交(非分层)近 12 个月 81 笔,中位 $1,200,000;标价约第 70 百分位。逐年中位 2021 $830k → 2026 $1,235k;5/10/20 年年化 10.1% / 8.1% / 5.2%;2001 起 4.9%。
- SQM postcode 2317:空置率 2026-09 0.89%(12 月均 1.27%,3 年前 0.51%);在售 46 房 + 30 单元(3 年前 23 + 15);房屋要价均 $1.10M、3 房 $919k;周租要价 $781。
- 可比 16 笔(价 $1.0–1.7M、地 590–1,225 m²、≤1.6 km、2025-04 起):上限参考 10 Kestrel Ave $1.70M(2000 年 241 m²、760 m² R2 无洪水,5/8);下限参考 9 Compass Cl $1.40M(1998 年 175 m²、800 m² R2 无洪水,5/8);同街旁证 136 Salamander Way $1.38M(1,117 m² C4 无洪水,4/8)。地价倍数中位 2.3,同街 2.25 × $632k ≈ $1.42M。
- 结论:合理区间 $1.28M–$1.42M;首次出价 $1.28M、放手 $1.37M、把握低–中;洪水为条件项(规划洪水位 vs 地板高度;保险报价)。

## 这次冷跑的计时与卡点(摘要)
人介入约 5 分钟;机器活跃约 80 分钟;墙钟 518 分钟(其中约 7.3 小时停在权限弹窗上)。17 条卡点里最重的两条:权限弹窗、council 配置只认整数图层号。两条都在 v0.3 修掉(SKILL.md 环境节;`nsw_layers.py` 字符串 id)。

---

# Worked example 2(unit):1803/150 Pacific Highway, North Sydney NSW 2060 · 冷跑 Run 4,2026-10-27/28

v0.3.1 对高层 strata unit 的冷跑,跑法只按 SKILL.md 字面;这次撞到的 17 条卡点变成了 v0.4 的「Unit path」。数字只用于对照方法,下一套房一律重查。

## 事实
| 项 | 值 | 来源 |
|---|---|---|
| 地块 | 单元 1803,SP 96878;Cadastre 点查多边形只是 224 m² 的 stratum 碎片(`hasstratum=2`);母地块 150 Pacific Hwy 在 SIXV L5 有 **两个 scheme**:propid 4161744(7,383 m²,LV $54.7M)与 4171107(4,441 m²,LV $11.5M),entitlement 需人 | CAD L9;SIXV L5(按母地址,4 行去重) |
| 分区 | MU1,North Sydney LEP 2013(`PCO_REF_KEY` 2013-411);限高 RL 125 m;无 FSR 值;TOD 686 m | EPI L2 / L5;SEPPH |
| 房型 | 2 卧 2 卫 1 车,室内 73 m²,产权面积 94 m²(室内 + 阳台 + 车位 + 储物),2018 年建,24 层楼 228 套住宅 + 商业裙楼,18 层角位 | Domain 档案页 + 挂牌文案 |
| 挂牌 | 指导价 $1,100,000(拍卖),2026-10-19 上架;上次成交 2018-10 $1,170,000 | Domain 档案页 + 挂牌页(id 从图片 URL 前缀反推) |
| Domain 免费估值 | $1.14M – $1.32M – $1.50M;租金估 $1,170/周;区中位 $1.04M;区均 41 天售出;空置 0.94% | Domain property-profile |
| 同楼成交史 | **206 笔**(2015 楼花期起,含 N/A),Domain 楼栋页 25 页一次取全;同竖列(尾号 03)11 笔;同户型最近 18 个月 8 笔 $1.10M–$1.45M(中位 $1.295M);同竖列 1503 $1.27M(2026-07) | `domain_building_profile.js` |
| 官方成交层 | VG L1 对本楼只有 2 笔(1503/150、204/150);`strata<>0` 逐年 2001–2019 每年 0–5 笔 → 不可用 | SIXV L1 |

## 风险
| 项 | 结果 | 来源 |
|---|---|---|
| 洪水 | **未覆盖**:council 只有 ArcGIS Online 分区层,洪水为 2022-11 PDF;州 HAZ L1 对 North Sydney 0 条 → 「免费数据未覆盖 · 下一步:10.7 证书 + PDF」 | `council-north-sydney.json` |
| 山火 | 未检出 ✓(州 BFPL;Balls Head 对照点亦空,层对 North Sydney 未验证) | Fire/BFPL L0 |
| 噪音 / 干道 | Pacific Hwy 32 m(functionhierarchy 2);AADT 需人 | TRANS L5 |
| 铁路 | 命中 186 m,实为 Sydney Metro Victoria Cross 隧道(`railontype=3`)→ 地面噪音无意义 | TRANS L7 |
| 规划 / 供应 | 300 m 内 DA ≥ $5M:105 Miller St 申报造价 $509M(2020 起 Under Assessment),可能遮挡东向景观 | DA_Tracking |
| Strata 体检 | strata report / levies 史 / 维修基金 / 缺陷(2018 年楼,6 年重大缺陷保修期将尽)/ cladding / 保险估值 → 付费或需人 | — |
| 公屋 / 犯罪 | ABS G37 SAL + SA2;BOCSAR 全州基线 | ABS;BOCSAR |

## 市场与可比
- 可比 11 笔(同楼同户型为主):上限参考 2007(L20,2025-07,$1.35M),下限参考同竖列 1503(L15,2026-07,$1.27M 略下调);其它楼成交无面积/楼层 → 三项全空,v0.4 起标「未知」折叠。
- 「两房 ≤ house 中位一半」在 North Sydney 自动通过但无判别力(独立屋每年 20–48 笔);硬信号改用楼内同户型自身增长:2018-10 $1.17M → 2026 $1.22M–1.27M ≈ +1 %/年,租金收益型资产。
- 结论:合理区间 $1.26M–$1.36M;首次出价 $1.22M、放手 $1.36M、把握中;指导价 $1.10M 比区间低 13–19%,是指导价口径,不是成交预期。最大风险不在洪水山火,在 strata 账本与 Pacific Hwy 噪音。

## 计时与卡点
需人 0 分钟;等权限 0;模型活跃约 110 分钟(含两个子代理 4 + 19 分钟);墙钟约 181 分钟(Aussie 同楼限速循环 16.6 分钟、VG 年度循环、BOCSAR 下载都在后台)。17 条卡点里 12 条是 unit 路径没写导致的(全部进了 v0.4 的 Unit path 与脚本 SP 分支)。
