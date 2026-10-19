# AI 基础设施供应链分类（v5 自编）

> 自编的 5 层分类，用于 `chain_map.layers[].taxonomy_code` 与 `subject.taxonomy_codes`。编码规则：`L<层>.<域>[.<细分>]`，全部大写。可自由扩展；新增代码时在本表追加一行即可。

## 层级与 Lens 的 `layer` 枚举对应

| 层 | 含义 | 对应 `layer` |
|---|---|---|
| L0 | 需求与根约束（资本开支方、电力、政策、原料） | `downstream_reference` / `cross_theme_root` |
| L1 | 上游：材料、设备、晶圆代工、先进封装 | `upstream_material` / `upstream_equipment` |
| L2 | 器件与芯片：加速器、存储、光电器件、被动件、基板 | `midstream_component` |
| L3 | 系统：服务器/机架、网络、散热、供电 | `midstream_system` |
| L4 | 平台与应用：云、模型、软件 | `downstream_reference` |

## 代码表

| 代码 | 节点 | 常见卡点原型 |
|---|---|---|
| L0.DEMAND | 超大规模云/模型公司资本开支 | — |
| L0.POWER | 数据中心电力、并网、燃机/核电 | ARC-CAPACITY-LOCK |
| L0.POLICY | 出口管制、补贴、关键矿产政策 | ARC-POLICY-MOAT |
| L0.RAW | 关键原料（镓、锗、铟、钨、高纯石英等） | ARC-RAW-MATERIAL |
| L1.MAT.SUBSTRATE | 化合物半导体衬底（InP、GaAs、SiC）、SOI 晶圆 | ARC-SOLE-SOURCE, ARC-RAW-MATERIAL |
| L1.MAT.GLASS | 玻璃纤维布（低 CTE / Low-Dk）、玻璃基板 | ARC-SOLE-SOURCE, ARC-TRANSITION-GATE |
| L1.MAT.CHEM | 光刻胶、电子气体、CMP 材料、ABF 膜 | ARC-SOLE-SOURCE |
| L1.EQP.FRONT | 前道设备（光刻、刻蚀、沉积） | ARC-CAPEX-PICKS-SHOVELS |
| L1.EQP.BACK | 后道设备（键合、模压、划片、HBM TCB） | ARC-CAPACITY-LOCK |
| L1.EQP.TEST | 测试、探针卡、量测检测 | ARC-CAPEX-PICKS-SHOVELS |
| L1.FAB | 先进制程晶圆代工 | ARC-SOLE-SOURCE |
| L1.PKG.COWOS | 2.5D/3D 先进封装（CoWoS、SoIC、EMIB 等） | ARC-CAPACITY-LOCK |
| L1.PKG.OSAT | 外包封测 | — |
| L2.ACCEL.GPU | GPU / AI 加速器 | — |
| L2.ACCEL.ASIC | 定制 ASIC / XPU | — |
| L2.ACCEL.CPU | 服务器 CPU | — |
| L2.MEM.HBM | 高带宽内存 | ARC-CAPACITY-LOCK |
| L2.MEM.STORAGE | DRAM/NAND/企业级 SSD | — |
| L2.OPT.LASER | 激光器芯片（EML、CW、VCSEL） | ARC-SOLE-SOURCE, ARC-HIDDEN-SUPPLIER |
| L2.OPT.MODULE | 光模块 | — |
| L2.OPT.CPO | 共封装光学、光纤阵列（FAU）、硅光 | ARC-TRANSITION-GATE |
| L2.CONN | 高速铜缆/AEC、连接器、Retimer | — |
| L2.PCB | 高多层 PCB、载板 | ARC-CAPACITY-LOCK |
| L2.PASSIVE | MLCC、电感、功率器件 | — |
| L3.RACK | 机架级系统与 ODM 组装 | — |
| L3.NET | 交换机、网卡 | — |
| L3.COOL | 液冷、冷板、CDU | ARC-TRANSITION-GATE |
| L3.PWR | 机架供电、UPS、变压器 | ARC-CAPACITY-LOCK |
| L4.CLOUD | 云/新云（Neocloud） | — |
| L4.MODEL | 模型公司 | — |
| L4.SW | 软件与应用 | — |

## 使用规则

1. 每个 Lens 的 `chain_map` 至少 3 层，且至少一层是上游（validate 强制）。
2. 节点的卡点原型必须引用 `references/serenity-playbook.md` 里的 `ARC-…` 编号（validate 强制）。
3. 未上市/子公司节点也要画出来（`listing_status`），它们常常决定上市公司的议价权。
