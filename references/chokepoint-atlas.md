# 卡点地图（Chokepoint Atlas）

> 由 `scripts/atlas.py render` 从 `assets/chokepoint-atlas.json` 生成，请勿手改。截至 2026-06-05。研究线索，不构成投资建议。代码为 Yahoo 风格，以实时解析为准。

状态是档案期的研究判断（见 `references/serenity-doctrine.md` §2），使用前用实时数据复核。

## AI 光子链（InP 激光 / 硅光 / CPO）（`ai_photonics`）

需求驱动：超大厂 AI 集群光互连：可插拔 800G/1.6T → CPO

| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |
|---|---|---|---|---|---|
| 高纯红磷 / 铟 / 6N-7N InP 多晶原料 `inp_raw` | L0.RAW | 正在卡·material | — | ARC-BOTTLENECK-OF-BOTTLENECK, ARC-RAW-MATERIAL | `4092.T` Nippon Chemical Industrial（高纯红磷龙头，serenity_lead）；`AXTI` AXT Inc.（自有原料/坩埚/前驱体（垂直整合），serenity_lead）；`5714.T` Dowa Holdings（原料/化合物材料，serenity_lead） |
| InP 衬底 `inp_substrate` | L1.MAT.SUBSTRATE | 正在卡·material | inp_raw | ARC-SOLE-SOURCE, ARC-RAW-MATERIAL | `AXTI` AXT Inc.（衬底双寡头之一（中国工厂），serenity_lead）；`5802.T` Sumitomo Electric（衬底双寡头之一（日本），serenity_lead）；`5016.T` JX Advanced Metals（衬底第三供应商，serenity_lead） |
| SOI / 硅光衬底 `soi_substrate` | L1.MAT.SUBSTRATE | 垄断不紧缺·demand | — | ARC-LICENSOR-MONOPOLY | `SOI.PA` Soitec（Smart Cut 许可方，serenity_lead）；`4063.T` Shin-Etsu Chemical（被许可方，serenity_lead） |
| 化合物外延片 `epiwafer` | L1.MAT.SUBSTRATE | 正在被订满·material | inp_substrate | ARC-WESTERN-SUBSTITUTE | `IQE.L` IQE（西方外延片（重组中），serenity_lead）；`3081.TWO` LandMark Optoelectronics（外延片，serenity_lead）；`4971.TWO` IntelliEPI（外延片，serenity_lead） |
| InP/GaAs 激光代工 `compound_foundry` | L1.FAB | 即将·material | epiwafer, inp_substrate | ARC-CAPACITY-LOCK | `3105.TWO` Win Semiconductors（化合物代工（低覆盖），serenity_lead） |
| 硅光代工 `siph_foundry` | L1.FAB | 正在被订满·demand | soi_substrate | ARC-CAPACITY-LOCK, ARC-REFERENCE-DESIGN | `TSEM` Tower Semiconductor（硅光代工，预订率高，serenity_lead）；`GFS` GlobalFoundries（硅光平台与参考设计，serenity_lead）；`XFAB.PA` X-FAB（特色代工，欧盟芯片法案映射，serenity_lead） |
| EML 激光（可插拔） `eml_laser` | L2.OPT.LASER | 正在卡·material | inp_substrate, epiwafer | ARC-FIRST-MOVER-LOCK | `LITE` Lumentum（EML 龙头，订满至 2028，serenity_lead）；`COHR` Coherent（综合厂（敞口被稀释），serenity_lead） |
| CW DFB 激光（硅光/CPO 光源） `cw_laser` | L2.OPT.LASER | 即将·demand | compound_foundry, inp_substrate | ARC-KINGMAKER, ARC-REFERENCE-DESIGN, ARC-DEMAND-SPILLOVER | `SIVE.ST` Sivers Semiconductors（无晶圆厂 CW 激光，serenity_lead）；`MTSI` MACOM（CW 激光，serenity_lead）；`AAOI` Applied Optoelectronics（自有 InP 激光，serenity_lead） |
| FAU / 光纤阵列与无源光器件 `fau_passive` | L2.OPT.CPO | 正在被订满·material | — | ARC-HIDDEN-SUPPLIER | `3363.TWO` FOCI Fiber Optic Communications（FAU，serenity_lead）；`HIMX` Himax（WLO/光学，serenity_lead） |
| 硅光/CPO 检测与良率 `siph_test` | L1.EQP.TEST | 即将·demand | — | ARC-TESTING-YIELD, ARC-FUNCTIONAL-MONOPOLY | `6830.TW` MSSCorps（CPO 检测，目标高份额，serenity_lead）；`FORM` FormFactor（探针/测试（领先指标），serenity_lead）；`AEHR` Aehr Test Systems（老化测试，认证转量产，serenity_lead）；`VIAV` Viavi Solutions（光测试（领先指标），serenity_lead） |
| CPO / 硅光封装 `cpo_packaging` | L1.PKG.OSAT | 正在被订满·demand | siph_foundry, cw_laser, fau_passive, siph_test | ARC-PARENT-CARRY | `6451.TW` Shunsin（鸿海体系 CPO 封装，serenity_lead）；`ASX` ASE Technology（OSAT，CPO 量产，serenity_lead）；`POET` POET Technologies（光学中介层（单一客户风险反例），serenity_lead） |
| CPO 连接器 / 笼体散热 `cpo_connector` | L2.CONN | 正在被订满·material | — | ARC-HIDDEN-SUPPLIER | `8147.TWO` Nextronics Engineering（卖方附注发现的微型股，serenity_lead） |
| 光模块 / 可插拔 `optical_module` | L2.OPT.MODULE | 正在被订满·material | eml_laser, cw_laser, fau_passive | ARC-DEMAND-SPILLOVER | `AAOI` Applied Optoelectronics（美国本土最大可用产能，serenity_lead）；`FN` Fabrinet（代工组装，serenity_lead）；`300308.SZ` Zhongji Innolight（光模块龙头，serenity_lead） |
| 光子 IP / 平台（CPO 交换、光计算） `photonic_platform` | L2.OPT.CPO | 即将·demand | cpo_packaging, optical_module | ARC-TRANSITION-GATE | `MRVL` Marvell（Celestial 光子互连，serenity_lead）；`AVGO` Broadcom（CPO 交换，serenity_lead）；`NVDA` NVIDIA（CPO 交换与需求方，serenity_lead） |

## AI 存储（HBM / NAND / 遗留 DRAM）（`memory`）

需求驱动：HBM 与企业级 SSD 挤占产能，推理带动存储需求

| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |
|---|---|---|---|---|---|
| 存储工序设备与 IP `mem_equipment` | L1.EQP.FRONT | 正在被订满·demand | — | ARC-EQUIPMENT-PHASE | `VECO` Veeco（激光退火，serenity_lead）；`RMBS` Rambus（接口 IP，serenity_lead）；`ONTO` Onto Innovation（量测，serenity_lead） |
| HBM 压缩成型 `hbm_molding` | L1.EQP.BACK | 垄断不紧缺·demand | — | ARC-FUNCTIONAL-MONOPOLY | `6315.T` Towa（压缩成型垄断，serenity_lead） |
| HBM / 先进 DRAM `hbm_dram` | L2.MEM.HBM | 正在卡·material | mem_equipment, hbm_molding | ARC-SUPER-SUPPLIER | `000660.KS` SK hynix（HBM 龙头，serenity_lead）；`005930.KS` Samsung Electronics（存储，serenity_lead）；`MU` Micron（存储，供给时间表来源，serenity_lead） |
| NAND / 企业级 SSD `nand` | L2.MEM.STORAGE | 正在卡·material | mem_equipment | ARC-SUPER-SUPPLIER | `SNDK` SanDisk（NAND 价格领导者，serenity_lead） |
| 遗留 DRAM / MLC NAND / NOR `legacy_memory` | L2.MEM.STORAGE | 正在卡·material | — | ARC-LEGACY-VOID | `2408.TW` Nanya Technology（遗留 DRAM，serenity_lead）；`2337.TW` Macronix（MLC NAND / NOR，serenity_lead）；`8299.TWO` Phison（库存套利，serenity_lead） |

## 先进封装与基板（CoWoS / 玻璃基板 / T-glass）（`advanced_packaging`）

需求驱动：AI 加速器封装面积与层数增长

| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |
|---|---|---|---|---|---|
| 高端玻璃纤维布（T-glass） `tglass` | L1.MAT.GLASS | 正在卡·material | — | ARC-FUNCTIONAL-MONOPOLY | `3110.T` Nitto Boseki（高端 T-glass 高份额，serenity_lead） |
| ABF 增层膜 `abf_film` | L1.MAT.CHEM | 垄断不紧缺·demand | — | ARC-SOLE-SOURCE | `2802.T` Ajinomoto（ABF 近垄断，提价空间，serenity_lead） |
| 玻璃基板（TGV / LIDE） `glass_core` | L1.MAT.GLASS | 即将·demand | — | ARC-FUNCTIONAL-MONOPOLY, ARC-QUAL-TO-VOLUME | `LPK.DE` LPKF Laser（LIDE 工艺设备，serenity_lead）；`011790.KS` SKC（玻璃基板（Absolics），serenity_lead） |
| CoWoS / 先进封装产能 `cowos` | L1.PKG.COWOS | 正在被订满·demand | tglass, abf_film, glass_core | ARC-CAPACITY-LOCK | `TSM` TSMC（价格制定者/锚，serenity_lead）；`AMKR` Amkor（第二来源封装，serenity_lead）；`BESI.AS` BE Semiconductor（混合键合设备，serenity_lead） |

## AI 电力（变压器 / 800V / 储能 / 发电）（`power`）

需求驱动：数据中心用电与并网瓶颈

| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |
|---|---|---|---|---|---|
| 变压器（干式/配电） `transformer` | L3.PWR | 正在卡·material | — | ARC-BACKLOG-COMPOUNDER, ARC-SOVEREIGN-BACKSTOP | `HPS-A.TO` Hammond Power Solutions（干式变压器，积压增长，serenity_lead） |
| 800V DC 功率器件（SiC/GaN） `hv_dc` | L3.PWR | 即将·demand | — | ARC-TRANSITION-GATE | `NVTS` Navitas（800V 合作伙伴中纯度最高，serenity_lead） |
| 储能系统 `storage_bess` | L3.PWR | 正在被订满·demand | — | ARC-HIDDEN-SUPPLIER | `FLNC` Fluence Energy（超大厂 MSA，serenity_lead） |
| 独立发电 / 表后电力 `power_gen` | L0.POWER | 正在卡·material | transformer | ARC-CAPEX-PICKS-SHOVELS | `VRT` Vertiv（电力与热管理（定价权例子），serenity_lead）；`LEU` Centrus Energy（美国唯一 HALEU，serenity_lead） |

## 关键矿产（出口管制清单 = 购物清单）（`critical_minerals`）

需求驱动：中国出口管制与西方供应链重建

| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |
|---|---|---|---|---|---|
| 锗 / 红外光学替代 `ge_substitute` | L0.RAW | 正在卡·material | — | ARC-WESTERN-SUBSTITUTE | `LPTH` LightPath Technologies（硫系玻璃替代锗，serenity_lead）；`TECK` Teck Resources（铟/锗，serenity_lead） |
| 稀土磁材 `rare_earth` | L0.RAW | 正在卡·material | — | ARC-SOVEREIGN-BACKSTOP, ARC-WESTERN-SUBSTITUTE | `MP` MP Materials（美国稀土，政府入股，serenity_lead）；`USAR` USA Rare Earth（本土磁材，serenity_lead） |
| 钨 / 锑 / 镓 / 铋碲 / 铍 `minor_metals` | L0.RAW | 正在卡·material | — | ARC-RAW-MATERIAL, ARC-WESTERN-SUBSTITUTE | `ALM` Almonty Industries（钨（Nasdaq: ALM；另在 TSX: AII.TO、ASX: AII.AX 上市），serenity_lead）；`UAMY` United States Antimony（锑，serenity_lead）；`VNP.TO` 5N Plus（铋/碲（“西方 AXTI”），serenity_lead）；`AA` Alcoa（镓，serenity_lead）；`MTRN` Materion（约 65% 铍，serenity_lead） |

## 人形机器人与自主系统（`robotics`）

需求驱动：人形机器人量产（5 年以上视角）

| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |
|---|---|---|---|---|---|
| 谐波减速器 / 执行器 `harmonic_reducer` | OTHER | 即将·demand | — | ARC-PER-UNIT-CONTENT | `688017.SS` Leaderdrive（国内谐波减速器龙头，serenity_lead）；`6324.T` Harmonic Drive Systems（西方谐波龙头，serenity_lead）；`002050.SZ` Sanhua Intelligent Controls（执行器，serenity_lead） |
| 精密力/应变传感 `force_sensing` | OTHER | 即将·demand | — | ARC-PER-UNIT-CONTENT | `VPG` Vishay Precision Group（单机价值量算术（设计出局风险），serenity_lead） |
| FMCW 4D 激光雷达 `fmcw_lidar` | L2.OPT.LASER | 即将·demand | — | ARC-TRANSITION-GATE | `AEVA` Aeva Technologies（FMCW 激光雷达（风投型），serenity_lead） |
| 认证材料 / 结构件 `robot_frames` | OTHER | 即将·demand | — | ARC-POLICY-MOAT | `SSYS` Stratasys（认证垄断（链底部），serenity_lead） |

## 国防 / 无人机 / 定向能（`defense`）

需求驱动：国防预算与无人机主导计划

| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |
|---|---|---|---|---|---|
| 高能激光 `directed_energy` | L2.OPT.LASER | 即将·demand | — | ARC-SOLE-SOURCE | `LASR` nLIGHT（首次实战验证，serenity_lead） |
| 水下探测 / 反水雷 `mine_countermeasure` | OTHER | 即将·demand | — | ARC-HIDDEN-SUPPLIER | `CODA` Coda Octopus（高毛利声呐，serenity_lead）；`EXA.PA` Exail Technologies（识别与处置，serenity_lead） |
| 军需分销合同通道 `food_distribution` | OTHER | 垄断不紧缺·demand | — | ARC-DISTRIBUTION-CHOKE | `SYY` Sysco（DLA 合同分销，serenity_lead）；`PFGC` Performance Food Group（DLA 合同分销，serenity_lead） |

## 量子（设备先行）（`quantum`）

需求驱动：超大厂量子项目研发期资本开支

| 节点 | 编码 | 状态 | 上游 | 原型 | 持有者 |
|---|---|---|---|---|---|
| MBE 外延设备 `mbe_tools` | L1.EQP.FRONT | 正在被订满·demand | — | ARC-EQUIPMENT-PHASE | `ALRIB.PA` Riber（MBE 双寡头之一，开源情报发现客户，serenity_lead）；`VECO` Veeco（MBE 双寡头之一，serenity_lead） |

