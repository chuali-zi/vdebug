# 面向调试 Agent 的嵌入式模拟虚拟环境程序深度调研与方案分析报告

## 执行摘要

本项目要解决的核心矛盾是：嵌入式软件调试经常被“硬件黑盒 + 物理现象不可见”拖慢——同一段固件在真实板子上表现为“没反应/偶发异常”，但根因可能只是软件层配置（引脚复用、外设时序、总线电气特性、RTOS 任务调度、初始化顺序、驱动参数等）与真实硬件预期不一致；而硬件侧又往往难以快速观测、复现实验与自动化回归。安全研究与大规模固件测试领域大量工作都在强调“脱离真实硬件的可重复仿真/重宿主（re-hosting）”与“外设建模”的价值，也同样指出外设与电气行为是主要难点与成本来源。citeturn6search0turn6search2turn6search4turn6search6

面向“调试 agent（如 IDE/代码 agent）”的可调用虚拟环境，建议的产品化落点不是“做一个全功能电路/SoC 仿真器”，而是做一个**轻量级、可脚本化、可插件扩展的虚拟硬件与文本化物理反馈层**：用“离散事件/状态机 + 必要的时序与电气规则”覆盖最常见的软件配置问题，同时提供对 agent 友好的接口（JSON Schema 校验、稳定错误码、可回放场景、可查询状态与日志）。与现有工具相比，**Renode** 强在“文本脚本/平台描述 + 外设模型 + CI 自动化”，**QEMU** 强在“通用系统仿真与设备模型框架 + QMP JSON 控制协议”，**Wokwi** 强在“面向开发者的电路图/交互式仿真 + CI 场景自动化 + 可用 C/WASM 扩展器件模型”。本项目可把这些成熟生态当作“后端选项/可插拔执行器”，而把主要创新集中在：**统一的 agent 调用协议、统一的设备抽象与“物理解释层（文本反馈）”**。citeturn0search0turn3search1turn8search1turn0search2turn0search6turn0search26turn8search2turn8search11

MVP（最小可行产品）建议优先走“两条轻量路径并行”：  
第一条是**host-native 重宿主**（例如让固件以主机可执行文件方式运行，类似 Zephyr 的 `native_sim` 思路），把 GPIO/UART/I2C/SPI/ADC 等“硬件 API”映射到你的虚拟环境，再叠加文本化反馈，快速覆盖大量“配置类问题”。citeturn0search3turn0search27  
第二条是**对接现成仿真器**（优先 Renode，其脚本与测试 API 友好；QEMU 作为后续增强），用你的接口层统一控制与观测，避免一开始就自研 CPU 与 SoC 级建模。citeturn0search4turn8search5turn8search12

对“大一新生”的可行性：**做“轻量可调用 + 常见外设 + 场景回放 + 文本反馈”的 MVP 是现实的**；但若目标升级为“通用 MCU 二进制无修改仿真 + 大量外设寄存器级精确模型 + 电路级 SPICE 联合仿真”，工程量会迅速接近 Renode/QEMU/EDA 工具级别，明显过于理想化。必须通过范围控制、复用现有后端、以“可解释反馈/可自动化回归”为主价值来把握可交付性。citeturn6search3turn6search7turn4search5turn3search1

---

## 项目目标与用例与接口形态

**项目目标（面向调试黑盒的“缩短定位时间”）**  
1) 把“硬件不可见”的调试过程变成可观测：不仅输出串口日志/寄存器状态，还能输出**文字化的电气/物理解释**（例如“此 I2C 读操作失败的可能原因：SDA 上拉缺失导致上升沿过慢，判定为总线保持低电平”）。I2C 的电气约束（如总线电容对上升沿与速率的影响）属于典型“软件配置问题最终表现为电气现象”的场景，适合做成规则化反馈。citeturn2search3turn2search31  
2) 让调试步骤可自动化复现：同一个“场景脚本（按钮按下/传感器变化/总线干扰）”可回放，并能集成到 CI。Wokwi 的“YAML 自动化场景 + CLI/CI”与 Renode 的“脚本 + Robot Framework 测试”证明这是成熟路径。citeturn0search26turn0search10turn0search4turn7search1  
3) 让 agent 易于调用：提供稳定协议（JSON Schema 校验、版本化）、可枚举能力（capabilities），以及“请求-响应 + 异步事件流”两种通道。

**典型调试场景（以“配置类问题”为主）**  
- GPIO：引脚方向/上下拉/复用错误导致外设不工作；反馈应指出“引脚当前模式与预期不符、冲突驱动/悬空”等（未指定需要电气级精确度，建议用规则与简化模型）。  
- UART：波特率/校验位/停止位不匹配导致乱码或 framing error；反馈不仅给“串口输出”，也给“可能的配置差异”。  
- I2C：地址错误、上拉缺失、时钟拉伸（clock stretching）处理不当、总线被某从设备拉低；反馈可结合 I2C 规范对电容/上拉策略的描述给出解释性文字。citeturn2search3turn2search31  
- SPI：片选极性/相位（CPOL/CPHA）错误、CS 时序不满足、MISO 悬空；反馈给“采样边沿/空读 0xFF/0x00 模式”等。  
- ADC/DAC：参考电压配置错误、量程溢出、采样时间导致读数不稳（若未指定模拟精度，建议先做“范围/噪声/饱和”近似）。  
- RTOS/并发：任务优先级与队列使用导致时序问题或死锁；可把关键调度事件结构化输出。FreeRTOS 文档对任务调度与队列机制有清晰抽象，可作为“事件语义”参考。citeturn5search0turn5search4  
- CI 回归：同一固件在每次提交后跑固定场景，确保关键 I/O 序列与输出一致；Zephyr 的 Twister 就是“在模拟环境（例如 QEMU）批量构建/运行测试”的典型。citeturn0search11

**agent 调用流程（建议的交互闭环）**  
1) `capabilities`：询问当前虚拟环境支持哪些总线/设备/物理规则、支持哪些后端（host-native / Renode / QEMU 等）。  
2) `create_session`：创建会话（选择硬件 profile、加载固件或 host-native 可执行文件、设定随机种子/确定性模式）。  
3) `load_scenario`：加载场景脚本（按钮/传感器/故障注入/时间推进）。Wokwi 支持用 YAML 描述自动化场景，属于可借鉴的表达方式。citeturn0search26turn0search6  
4) `run/step`：推进仿真时间（离散事件），或运行到断点/条件；必要时允许对接 GDB（Renode 可在脚本中启用 GDB server；QEMU 也支持通过 gdbstub/semihosting 进行调试集成）。citeturn8search29turn0search1  
5) `observe`：拉取结构化观测（引脚状态、总线事务、寄存器影子值、队列事件）+ 文本化物理反馈（human-readable “why”）。  
6) `export_artifacts`：导出日志、事件流、最小复现场景（供 agent 写回修复建议）。

**输入/输出格式（未指定处明确标注）**  
- JSON：**指定（建议作为主数据模型）**；同时建议用 JSON Schema 做参数校验与文档化。JSON Schema 2020-12 是当前版本线之一。citeturn2search5turn2search1  
- REST（HTTP）：**指定（建议提供）**；用 OpenAPI 描述接口以便自动生成客户端与文档。OpenAPI 定义“语言无关的 HTTP API 描述”，适合作为 agent/工具链集成入口。citeturn2search4turn2search16  
- CLI：**指定（建议提供）**；用于人类快速复现与 CI 执行（类似 Wokwi CLI 的定位）。citeturn0search6turn3search10  
- IPC：**指定（建议提供）**；本地优先用 Unix domain socket（权限与本机通信效率好），或 stdio（最利于被“工具调用/子进程”模式集成）。AF_UNIX 的用途在 Linux man-pages 中有明确说明。citeturn5search3  
- 其他：gRPC/Protobuf **未指定（建议作为可选增强）**；其典型模式是 `.proto` 定义服务并生成多语言客户端，适合高吞吐、长连接与严格类型。citeturn2search14turn2search18  
- 其他：MCP（Model Context Protocol）**未指定（但强烈建议纳入兼容层）**；MCP 以“工具（tools）暴露 + JSON Schema 描述参数”方式对接多种客户端，并且可走 stdio/JSON-RPC 等传输，天然贴合“agent 可调用工具”。citeturn1search11turn1search39turn1search23

---

## 现有工具与竞品调研

下表按“与你要做的能力维度”对比常见方案（既包含工程工具，也包含电路/建模工具与相关研究路线）。由于你目标强调“轻量 + 可被 agent 调用 + 文本化物理反馈”，表中把“是否易于脚本/CI/接口化”作为重点，而不是单纯仿真精度。

| 工具/路线 | 主要定位 | 轻量性（定性） | 可扩展性 | 语言/平台要点 | 许可/商业 | 文本化物理反馈 | agent 调用友好度 |
|---|---|---|---|---|---|---|---|
| QEMU | 通用系统仿真/虚拟化与设备仿真框架；提供 HMP（人类）与 QMP（JSON）管理接口 | 中-重（取决于机器/设备模型） | 强：设备模型/命令体系；QMP 适合外部控制 | QMP 明确是 JSON 协议，可供工具控制；QEMU 文档区分 HMP/QMP | GPLv2（含部分其他许可）citeturn3search1 | 以功能行为为主，电气解释通常需自建规则层 | 高：QMP 为 JSON 控制协议，易做自动化citeturn8search5turn8search31turn8search12 |
| Renode | 面向嵌入式/多节点系统的仿真框架；脚本/平台描述文本化；强 CI/测试 | 中（比全 EDA 轻，仍非“极轻”） | 强：外设模型、平台描述 `.repl`、脚本 `.resc`，可接 Verilator 等 | `.repl` 是类 YAML 的平台描述格式；`.resc` 用于可重复脚本；与 Robot Framework 集成测试 | MIT（框架本体）citeturn4search5turn4search1 | 可通过测试 API/脚本生成“解释性输出”，但默认不等于电气解释层 | 高：脚本化 + 测试 API + 可放进 CIciteturn8search2turn8search11turn0search4turn0search0 |
| Wokwi | 面向开发者的嵌入式仿真（IDE/浏览器），支持 CI、自动化场景与自定义器件模型 | 轻-中（对用户体验友好） | 强：自定义芯片 API（C/WASM 等）、YAML 场景自动化 | VS Code 集成；CI/CLI；自定义芯片可用 C 或可编译到 WASM 的语言；项目配置含 `wokwi.toml` 与 `diagram.json` | 服务与许可证/定价为商业化体系；但 `wokwi-cli` repo 可见 MIT 等组件 | 具备“电路图 + 交互”语义，较容易产出可读反馈，但是否“电气解释”取决于自建规则 | 高：CLI + 场景脚本很适合 agent 驱动citeturn0search2turn0search6turn0search26turn0search22turn3search14turn3search2turn3search10turn0search38 |
| Zephyr `native_sim`/POSIX 目标 + Twister | 把嵌入式应用编译成主机可执行文件；Twister 可批量在模拟环境跑测试 | 轻 | 中：靠驱动抽象/仿真驱动扩展 | `native_sim` 生成普通 Linux 可执行文件；Twister 可在如 QEMU 的环境跑测试 | 开源 | 可以很容易把“物理解释层”写成 host 侧日志/断言 | 高：天然适合 CI 与自动化回归citeturn0search3turn0search11turn0search27turn0search15 |
| simavr | AVR 侧的“lean/mean”仿真器，可产出波形/调试 | 轻 | 中：偏特定架构 | 强调 small/compact/hackable；manpage 提及可执行固件、产出 VCD、调试 | GPLv3（本体） | 可输出波形/状态，但电气解释仍需自建 | 中：可脚本化，但生态面向 AVR 专用citeturn1search0turn4search10turn1search36 |
| ngspice | SPICE 电路仿真（混合信号/电路级），含控制语言/脚本能力 | 中（电路复杂度越高越重） | 强：适合“电气真实性”，但与固件联合需集成 | 官方手册覆盖功能/命令；许可为 BSD（大体） | BSD（代码为主） | 强：天然能给电压/电流等“物理量”，但与 MCU 软件联动成本高 | 中：可批处理/脚本，适合做“电气后端”可选项citeturn1search17turn4search3turn1search13turn1search21 |
| Verilator（+协同仿真） | 把 Verilog/SystemVerilog 转为 C++/SystemC 的周期级模型；常用于高性能数字逻辑仿真 | 中（编译后运行快，但工具链复杂） | 强：适合对某些外设/加速器做精确数字模型 | 官方说明其将 HDL 转为可执行模型；许可证 LGPLv3 或 Artistic 2.0 | LGPLv3/Artistic | 可输出数字波形/覆盖率；物理解释需上层 | 中：适合作为“可选精确设备插件后端”citeturn1search30turn3search3turn1search10turn8search33 |
| Proteus VSM（商业） | MCU 模型 + SPICE 混合仿真、面向原理图协同仿真 | 中-重 | 中 | 官方材料强调“混合模式 SPICE + MCU 模型协同仿真” | 商业 | 较强（面向电路/原理图） | 低-中：更偏 GUI 工作流，非 agent 优先citeturn9search3turn9search0 |
| Simulink（商业） | 多域建模与仿真、模型驱动设计、可生成代码与测试工作流 | 重 | 强（生态大） | 官方说明其用于多域模型与“仿真后再上硬件/部署” | 商业 | 可做到很强的解释与可视化，但不“轻量” | 中：可通过脚本/API，但部署重量很大citeturn9search21turn9search10 |
| HALucinator / P2IM / avatar2（研究路线） | 针对固件重宿主、外设建模、动态分析/模糊测试等，强调摆脱真实硬件 | 研究用途：从中到重 | 方法论强，但工程实现门槛高 | HALucinator 强调用 HAL 抽象拦截硬件依赖；P2IM 强调自动外设接口建模；avatar2 强调编排 QEMU/GDB/OpenOCD 等多目标 | 多为开源/论文实现 | 可输出“解释性日志”，但更偏分析与 fuzz | 中：可借鉴“抽象/拦截/模型生成”的思想作为你的“反馈层/建模策略”citeturn6search0turn6search2turn6search5turn6search8 |

关键信息归纳：  
- 若你要“轻量 + 易被 agent 调用 + 强可复现”，**Wokwi（CLI+场景）**与 **Renode（脚本+Robot Framework）**是离目标最近的现成范式；但二者都不直接提供你设想的“统一的文本化物理解释层”，这正是可差异化点。citeturn0search26turn0search4turn0search6turn8search2  
- 若你要“标准化机器控制协议”，QEMU 的 **QMP（JSON）**是对照标杆：你可以类比 QMP 的思路，把你的虚拟硬件抽象为“可查询、可事件推送、可版本协商”的对象模型。citeturn8search5turn8search31turn8search12  

---

## 必要背景知识与学习清单

下面按“必须 / 推荐 / 可选”给出学习主题与资源（资源以官方/权威为主；若存在中文材料则优先，未指定处不强求）。

| 分类 | 主题 | 为什么与本项目直接相关 | 建议资源（链接以引用形式提供） |
|---|---|---|---|
| 必须 | GPIO/UART/I2C/SPI/ADC 的软件抽象与常见坑 | 这是你要虚拟化的主要外设面；“文本化反馈”需要能把错误映射回配置原因 | Zephyr 驱动 API/接口文档（GPIO/I2C/SPI/UART/ADC 等接口与模拟接口条目可做抽象参考）citeturn5search14turn5search22turn5search34；I2C 规范（电气与协议细节）citeturn2search3turn2search31 |
| 必须 | 基本电路与电气概念（上拉/下拉、开漏、RC、阈值、噪声、参考电压） | 你的“物理/电物理文字反馈”需要最小电气模型，尤其 I2C 这类强电气约束总线 | I2C-bus specification & user manual（含总线电容与设计策略等）citeturn2search3turn2search31；（可选补充）ngspice 作为电路仿真参考后端citeturn1search17turn4search3 |
| 必须 | 嵌入式裸机/RTOS 基础（任务、调度、队列/中断与时序） | 你要把“时序/并发”转为可观测事件流；同时要能构造可回放的测试场景 | FreeRTOS 任务调度与队列文档citeturn5search0turn5search4turn5search24；Zephyr `native_sim`（把嵌入式应用编成主机可执行文件）citeturn0search3turn0search27 |
| 必须 | 网络/IPC（进程间通信、权限、协议与版本化） | agent 通常通过本地进程或 socket 调用；你需要可靠、可测试的 IPC | Unix domain socket（AF_UNIX）说明citeturn5search3；若走 HTTP，建议用 OpenAPI 管理契约citeturn2search4turn2search16 |
| 推荐 | API 契约与数据验证（OpenAPI / JSON Schema） | 这是让 agent“低摩擦调用”的关键；能自动生成文档/客户端并减少参数错误 | OpenAPI 规范citeturn2search4turn2search16；JSON Schema 规范（2020-12）citeturn2search5turn2search1 |
| 推荐 | 测试与CI（pytest/Robot Framework/Twister） | 你的系统价值之一是“复现与回归”；应从第一天就把“场景脚本 + 断言”跑在 CI | Robot Framework 用户指南（关键字驱动）citeturn7search1；Renode 与 Robot Framework 集成说明citeturn0search4turn3search8；Zephyr Twisterciteturn0search11；pytest 文档citeturn7search3 |
| 推荐 | 语言与框架：Python/ Rust / C/C++ 的接口桥接 | 你可能需要：快速开发（Python）、高性能/安全（Rust）、与固件/仿真器对接（C/C++） | gRPC/Protobuf（若走强类型 RPC）citeturn2search14turn2search18；MCP（若做 agent 工具接口）citeturn1search11turn1search39 |
| 可选 | SPICE/混合仿真（ngspice/Qucs-S/LTspice） | 若你未来要更真实的模拟量/电路反馈，可把它做成“后端插件”而非 MVP 强依赖 | ngspice 手册/控制语言citeturn1search17turn1search13；Qucs-S 文档（把 ngspice 等作为后端）citeturn9search7turn9search2；LTspice 指南（如需参考商业工具的交互与术语）citeturn9search1 |
| 可选 | HDL/周期级模型（Verilator + cocotb） | 若要对某些外设/加速器做更精确数字逻辑模型，可作为高级插件路线 | Verilator 文档与许可信息citeturn1search30turn3search3；cocotb 文档（用 Python 写协同仿真测试平台）citeturn7search0 |

---

## 技术栈与实现选项

本节把你的关键决策拆成四个“可替换轴”：运行时形态、通信协议、设备建模方法、可观测性/性能目标。核心建议是：**把“仿真后端”与“对 agent 的统一接口/反馈层”解耦**，后端可以是你自研的轻量内核，也可以接 Renode/QEMU/Wokwi 等。

**运行时选项（本地进程 / 容器 / 云）**  
- 本地进程：最轻、启动快，适合 IDE/agent 作为子进程启动；配合 Unix domain socket 或 stdio 最自然。AF_UNIX 适合同机进程高效通信与权限控制。citeturn5search3  
- 容器：牺牲少量启动成本换可复现实验环境（工具链/依赖固定）；适合 CI。  
- 云：适合重仿真或并行跑大量场景，但会引入鉴权、带宽与隐私问题（未指定是否需要云，建议先不做）。

**通信协议选项（REST / gRPC / Unix socket / stdin/stdout / 语言绑定）**  
- REST + OpenAPI：生态广、调试方便、易被 agent 通过 HTTP 客户端调用；OpenAPI 能把接口契约标准化并生成客户端。citeturn2search4turn2search16  
- JSON-RPC over stdio（MCP 风格）：非常适合“agent 以子进程工具方式调用”；MCP 的工具定义以 JSON Schema 描述参数，有利于强约束与自动化。citeturn1search11turn1search39turn1search23  
- gRPC + Protobuf：更严格类型、更高吞吐、自动生成多语言 client/server；gRPC 以 `.proto` 为中心并生成代码。citeturn2search14turn2search18  
- Unix socket（自定义协议/HTTP over UDS）：本地性能和权限好；但跨平台（Windows）与代理稍复杂（未指定跨平台要求，建议先以 Linux/macOS 为主）。citeturn5search3  

**设备模型选项（事件驱动 / 时序仿真 / 状态机 / 信号级）**  
- 状态机（transaction-level）：把 I2C/SPI/UART 看成“字节/事务”层的交互，适合定位配置问题（地址/模式/速率/时序约束），MVP 推荐。  
- 离散事件时序（discrete-event）：引入统一虚拟时间与事件队列，能表达超时、竞争、调度、抖动；适合做“可回放场景”。  
- 信号级/周期级：更接近硬件真实，但成本高。Verilator 明确提供“周期级模型（cycle-accurate）”并生成可执行 C++/SystemC 模型，是典型信号/周期级路线。citeturn1search30turn1search2  
- 电路级（SPICE）：最强调物理量，但性能与建模成本高。ngspice 提供完整手册与控制语言，适合作为“可选电气后端”。citeturn1search17turn1search13turn4search3  

**日志/可视化与性能目标（轻量级建议）**  
- 可视化：未指定是否必须 GUI。建议 MVP 只做“结构化日志 + 可查询状态 + 可导出事件流”，把 GUI 作为后续（可以对接现有 IDE 或 Web）。  
- 性能/资源占用：未指定“轻量级”定义。建议给出可量化目标（例如：冷启动 < 1s；常驻内存 < 200MB；单场景 10^5 事件推进 < 数秒；日志可采样/限速）。这些是工程目标而非标准事实，需在实现中校准。  
- 产物格式：可参考 simavr 等工具支持导出波形（如 VCD）用于深入排查；simavr 的 manpage 提到可产生 VCD 波形与调试会话。citeturn1search36  

**优缺点对比表（面向你项目的三条主实现路线）**

| 路线 | 核心思路 | 主要优点 | 主要缺点 | 适合阶段 |
|---|---|---|---|---|
| Host-native 重宿主（优先） | 让固件/业务逻辑作为主机进程运行；硬件 API 接到你的虚拟环境 | 极轻、调试体验好、易做 CI；非常适合排查软件层配置问题 | 与真实 MCU 指令级差异大；对“二进制无修改仿真”覆盖有限 | MVP 到长期（作为快速回归层）citeturn0search3turn0search27turn0search11 |
| Renode/QEMU 作为仿真后端 | 你做统一接口/反馈层，后端执行交给 Renode 或 QEMU | 复用成熟生态；可接近真实固件运行；脚本与自动化能力强（Renode尤甚） | 学习曲线与集成复杂度高；外设模型精度/覆盖取决于后端与平台 | 中期增强citeturn8search2turn8search11turn8search5turn8search12 |
| 混合后端（SPICE/HDL 共仿） | 对少数关键外设/电气行为用 ngspice/Verilator 等精确后端 | 可获得更可信的“物理量”与时序细节 | 工程量大，性能与模型维护成本高 | 后期/研究向citeturn1search17turn1search30turn8search33 |

---

## 系统架构设计与接口示例

**模块划分（建议的可维护边界）**  
1) **核心仿真内核（Simulation Core）**：统一虚拟时间、事件队列、确定性（seed）、调度策略（离散事件推进/步进/运行到条件）。  
2) **设备插件（Device Plugins）**：GPIO/UART/I2C/SPI/ADC/DAC + 常用器件（EEPROM、温湿度传感器、SPI Flash 等）。插件只关心“设备语义”，不关心 agent 协议。  
3) **物理解释层（Physics/EE Explanation Layer）**：把低层现象（如 I2C NACK、总线一直为低、超时）映射成“可读原因链 + 建议排查项”；规则来源可以来自协议规范与工程经验（例如 I2C 总线电容/上拉策略）。citeturn2search3turn2search31  
4) **agent 接口层（Agent API Gateway）**：统一提供 REST(OpenAPI) 与 JSON-RPC(stdio) 两套入口；内部都映射到同一“命令/事件”模型。OpenAPI 适合 HTTP 契约化；MCP 风格适合工具化调用与 JSON Schema 校验。citeturn2search4turn2search16turn1search11turn1search39  
5) **脚本/场景管理（Scenario Engine）**：加载“动作序列 + 断言 + 触发条件”，支持回放/最小化复现；可参考 Wokwi 的 YAML automation scenarios 与 Renode 的 `.resc` 脚本思路。citeturn0search26turn8search11  
6) **持久化与工件（Artifacts Store）**：保存日志、事件流、配置快照、可复现包（scene + firmware + seed）。  
7) **测试 Harness 与安全/沙箱**：把场景当测试；CI 中跑；对插件执行做隔离（未指定安全要求，建议至少做“插件权限/资源限制”）。Renode 已证明“仿真纳入 CI”是可行路径；Wokwi 也提供 CI 工作流。citeturn0search4turn0search10turn3search8turn3search26  

**模块关系/数据流图（Mermaid）**

```mermaid
flowchart LR
  A[Agent / IDE Assistant] -->|REST(OpenAPI) / JSON-RPC(stdio)| G[Agent API Gateway]
  G --> C[Command Router]
  C --> S[Session Manager]
  S --> K[Simulation Core\n(time + event queue)]
  K --> P[Device Plugins\n(GPIO/UART/I2C/SPI/ADC...)]
  P --> E[Physics/EE Explanation Layer\n(rule-based hints)]
  K --> L[Structured Logs & Event Stream]
  E --> L
  S --> R[Scenario Engine\n(YAML/DSL replay + asserts)]
  R --> K
  L --> D[Artifacts Store\n(logs/traces/repro bundle)]
  S --> B[(Optional Backend)\nRenode/QEMU/Wokwi adapters]
  B --> K
```

**接口风格建议（对 agent 友好的一致性约束）**  
- 每个命令返回：`ok`/`error`、稳定 `error_code`、可机器解析的 `details`、可读的 `explain`（给物理解释）。  
- 所有输入参数用 JSON Schema 校验；Schema 版本化（例如 `v1alpha1`）。JSON Schema 的定位是“定义结构、校验与文档化”。citeturn2search9turn2search5  
- REST 接口用 OpenAPI 生成文档与客户端；OpenAPI 的定义目标就是让人和机器无需读源码即可理解 API。citeturn2search4turn2search16  

**示例 REST API（建议）**  
- `POST /v1/sessions`：创建会话（固件/目标/后端/seed）  
- `POST /v1/sessions/{sid}/scenario:load`：加载场景  
- `POST /v1/sessions/{sid}/step`：推进时间或执行步进  
- `GET /v1/sessions/{sid}/state`：获取结构化状态  
- `GET /v1/sessions/{sid}/events?since=...`：拉取事件流  
- `POST /v1/sessions/{sid}/io/gpio:set`、`/io/i2c:transact`、`/io/uart:write` 等

**示例 JSON Schema（请求/响应骨架，Draft 2020-12 风格；未指定字段可扩展）**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.local/schemas/v1/command.json",
  "title": "SimCommand",
  "type": "object",
  "required": ["session_id", "cmd", "params"],
  "properties": {
    "session_id": { "type": "string", "minLength": 1 },
    "cmd": {
      "type": "string",
      "enum": ["step", "gpio.set", "gpio.get", "uart.write", "i2c.transact", "spi.transact", "adc.read"]
    },
    "params": { "type": "object" },
    "request_id": { "type": "string" }
  },
  "additionalProperties": false
}
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.local/schemas/v1/response.json",
  "title": "SimResponse",
  "type": "object",
  "required": ["ok", "request_id"],
  "properties": {
    "ok": { "type": "boolean" },
    "request_id": { "type": "string" },
    "data": { "type": "object" },
    "error": {
      "type": "object",
      "required": ["error_code", "message"],
      "properties": {
        "error_code": { "type": "string" },
        "message": { "type": "string" },
        "details": { "type": "object" },
        "explain": { "type": "string" }
      }
    }
  },
  "additionalProperties": false
}
```

**简短代码片段（Python 例：通过 REST 驱动一步 I2C 事务）**

```python
import requests

BASE = "http://127.0.0.1:8787"

# 1) create session
sid = requests.post(f"{BASE}/v1/sessions", json={
    "backend": "host-native",  # or "renode"/"qemu" (未指定：按实现支持)
    "seed": 42,
    "firmware": {"type": "elf", "path": "./build/app.elf"}
}).json()["session_id"]

# 2) i2c transact
resp = requests.post(f"{BASE}/v1/sessions/{sid}/io/i2c:transact", json={
    "bus": "i2c0",
    "addr_7bit": 0x48,
    "write": [0x00],
    "read_len": 2,
    "timeout_ms": 10
}).json()

if not resp["ok"]:
    print("ERROR:", resp["error"]["error_code"], resp["error"]["message"])
    print("HINT :", resp["error"].get("explain"))
else:
    print("DATA:", resp["data"])
```

---

## 开发路线、里程碑与可行性评估

**分阶段 MVP 功能清单与交付物（时间为经验性估算，未指定团队背景时按“2–4人学生团队、每周 10–15 小时/人”保守评估）**  
- 阶段一：接口与会话骨架（2–3 周）  
  交付物：  
  - REST(OpenAPI) + JSON-RPC(stdio) 双入口（至少一个先落地）；JSON Schema 校验；错误码规范；事件流通道（轮询或 SSE/WS，未指定可先轮询）。citeturn2search4turn2search16turn2search5turn1search11turn1search39  
  - 最小 Session Manager：创建/销毁/导出工件。  
  测试用例示例：  
  - “非法参数被 JSON Schema 拒绝”；“同一 request_id 幂等返回”；“capabilities 返回稳定字段”。  

- 阶段二：轻量仿真内核 + GPIO/UART（3–4 周）  
  交付物：  
  - 离散时间推进（`step(ms)`）、事件队列；GPIO 状态机（输入/输出/上拉/开漏简化）；UART 字节流（波特率作为元数据，不做真实采样也可）。  
  - 文本化反馈 MVP：如“GPIO 未配置为输出导致写入无效”。  
  测试用例示例：  
  - “GPIO 写入后可读回”；“UART 输出匹配期望文本（类似 Wokwi CI 的 expect_text 思路）”。citeturn3search26turn0search26  

- 阶段三：I2C/SPI/ADC 基础建模 + 场景回放（4–6 周）  
  交付物：  
  - I2C：支持地址、读写事务、NACK/timeout、上拉缺失/总线被拉低等规则化判定；把 I2C 规范中的电气风险（电容、上升沿策略）转成解释文本。citeturn2search3turn2search31  
  - SPI：CPOL/CPHA/CS 规则化校验与典型错误输出。  
  - ADC：范围/参考电压/噪声/饱和的简化模型（未指定精度时不做 SPICE）。  
  - Scenario Engine：YAML/DSL（可参考 Wokwi YAML 场景）驱动按钮、传感器变化、故障注入、断言串口输出。citeturn0search26  
  测试用例示例：  
  - “I2C 总线被拉低时给出 explain=‘检查上拉/从设备占线’”；“SPI 模式不匹配时指出 CPOL/CPHA 差异”。  

- 阶段四：对接现成后端（Renode 优先，6–10 周，可与阶段三后半并行）  
  交付物：  
  - Renode Adapter：把你的 `step/observe/io` 映射到 Renode 脚本与测试 API；支持加载 `.repl/.resc`，并把关键事件转进你的统一事件流。Renode 的 `.repl`/`.resc` 文档与测试集成是可直接复用的参考。citeturn8search2turn8search11turn0search4turn8search0  
  - 可选：QEMU Adapter：用 QMP（JSON）做控制面，统一为你的命令模型。QEMU 文档明确 QMP 是可版本化的机器接口，并区分 HMP/QMP。citeturn8search5turn8search31turn8search12  
  测试用例示例：  
  - “同一场景在 host-native 与 Renode 后端产生一致的高层事件序列（允许底层差异）”。  

**对大一新生可行性评估（关键在范围控制）**  
- 学习曲线：  
  - “能跑起来并被 agent 调用”的难点主要在工程组织与协议设计（API 契约、错误码、日志与测试），而不是硬件本身；OpenAPI/JSON Schema/MCP 这类标准能显著降低接口问题的试错成本。citeturn2search4turn2search5turn1search11  
  - “能给出像工程师一样的文本化物理解释”的难点在把协议/电气知识固化成规则（例如 I2C 的电容、上升沿与速率约束）。citeturn2search3turn2search31  
  - “做成通用 MCU 仿真器”的难点在外设建模工作量，研究界也反复指出精确 MMIO/外设模型代价高。citeturn6search3turn6search7  

- 先修课程建议（未指定你的课程进度时给最低集合）：C 语言与数据结构、计算机组成（基本总线/中断概念）、操作系统基础（进程/线程/IPC）、电路基础（欧姆定律、RC、开漏/上拉）。  
- 团队规模建议：  
  - 2 人可完成“接口 + host-native + 少量设备 + 文本反馈”；  
  - 3–4 人更合理：可分成“接口/协议与CI”、“仿真内核与设备模型”、“反馈规则与场景库”、“Renode/QEMU 对接”。  
- 主要风险与缓解：  
  - **范围失控**：一上来追求通用二进制仿真与大量外设寄存器级精确模型 → 缓解：MVP 明确只覆盖“配置类问题”与少量外设，并优先对接现成后端（Renode/QEMU）。citeturn4search5turn3search1turn0search4  
  - **反馈不可用（太玄学）**：文本提示若不与可观测证据绑定会失去可信度 → 缓解：每条 explain 必须链接到结构化证据（例如“观测到 SDA 连续 X ms 为低且无上升沿”）。  
  - **测试缺失导致不可控**：仿真系统若无回归测试会快速腐化 → 缓解：从阶段一就把场景当测试，参考 Wokwi CI 与 Renode+Robot 的自动化范式。citeturn0search10turn0search26turn0search4turn3search8  

**资源与工具清单（优先开源/可自动化）**  
- 仿真/后端候选：Renode（脚本与平台描述 `.repl`、脚本 `.resc`、测试集成）citeturn8search2turn8search11turn0search4；QEMU（QMP JSON 控制协议）citeturn8search5turn8search12；Wokwi（CLI + YAML 场景 + 自定义器件模型 API）citeturn0search6turn0search26turn0search22；Zephyr `native_sim`（host-native）citeturn0search3turn0search27  
- 电气/模型后端（可选）：ngspice（BSD 许可、手册与控制语言）citeturn4search3turn1search17turn1search13；Verilator（周期级数字模型、LGPL/Artistic）citeturn1search30turn3search3  
- 测试框架：pytestciteturn7search3；Robot Frameworkciteturn7search1；若用 C++：GoogleTestciteturn7search2；若做 HDL：cocotbciteturn7search0  
- CI/CD 建议：GitHub Actions + 场景回放；可参考 Wokwi CI 与 Renode GitHub Action 的公开实践。citeturn0search10turn3search26turn3search8  

**额外建议（让 agent 更高效调用、让 skill 可复用）**  
- “可复用 skill”的关键是把工具能力切成稳定原语：`step`、`observe`、`inject_fault`、`set_sensor`、`assert_serial`、`export_repro`，并用 JSON Schema 约束参数与返回形状；MCP 的“tools 以 schema 描述”正是这一套思路的标准化表达（未指定必须使用，但兼容价值高）。citeturn1search11turn1search39  
- 让 agent 少走弯路的接口设计要点：  
  - **强约束**：参数枚举、单位字段（ms/Hz/V）、显式版本；  
  - **可探索**：`capabilities` 与 `list_devices/list_buses`；  
  - **可解释**：每个错误给“证据字段（observations）+ explain（人类可读）+ next_actions（可执行建议）”；  
  - **可回放**：每次失败都能导出“最小复现包”（scene + seed + 固件哈希 + API 调用序列）。  
- 未来扩展方向（按投入产出排序）：  
  1) 设备库与场景库（比提升仿真精度更能直接降低调试成本）；  
  2) Renode/QEMU 适配增强（覆盖更多真实固件运行形态）；  
  3) “电气后端插件”（ngspice）用于少数关键模拟问题；  
  4) 周期级外设插件（Verilator）用于高精度数字外设/加速器；  
  5) 借鉴 P2IM/HALucinator 等研究路线，在“外设响应缺失”时用启发式/学习式生成模型（但这会显著提高研究与工程门槛）。citeturn6search2turn6search0turn6search3