# AI Agent System Prompt / Architecture Index

你现在接手的是一个“面向 agent 的、可脚本化、可解释的嵌入式虚拟调试平台”项目。你的首要任务不是追求全量仿真精度，而是按 MVP 闭环优先原则推进一个可实现、可调试、可回归的系统。

## 1. 项目一句话定义

这是一个帮助 agent 自主调试嵌入式设备的软件平台。平台通过虚拟设备环境模拟 GPIO、UART、I2C 等总线与设备行为，让 agent 能以统一接口执行调试动作、注入场景、读取状态、获取证据绑定的解释，并导出最小复现包。

## 2. 你的默认工作规则

1. 先按 MVP 架构理解项目，再考虑长期扩展。
2. 当前默认只做 `Mode A: Device-Simulation`。
3. 当前默认技术路线是 `Python + FastAPI + Pydantic + YAML + 文件存储`。
4. 当前默认只覆盖 `GPIO / UART / I2C`。
5. 解释必须绑定事件证据或诊断事实，不能凭空猜测。
6. 默认优先做完整闭环，不优先做 MCP、Renode、QEMU、WebSocket 或复杂工程外壳。

## 3. 文档优先级

如果本目录内容与原始仓库文档存在重叠，按下面顺序理解：

1. `architecture_mvp_simplified.md`
2. `architecture_report_v2_new.md`
3. `architecture_modules_map_new.md`
4. `architecture_report_new.md`
5. `deep-research-report (2).md`

本目录中的 8 份模块报告已经按这个优先级重新整理。

## 4. 当前实施基线

项目当前实施基线不是 24 个长期模块同时落地，而是 8 个 MVP 模块：

1. `api`
2. `session`
3. `board`
4. `engine`
5. `devices`
6. `diagnosis`
7. `scenario`
8. `artifacts`

长期 24 模块是未来升级路线，本目录中的每份报告都给出了与长期模块的映射关系。

## 5. 8 个模块如何协作

主链路：

`api -> session -> board -> engine -> devices -> diagnosis -> artifacts -> api`

场景链路：

`api -> scenario -> engine -> devices -> diagnosis -> scenario -> artifacts`

其中：

1. `api` 负责统一入口与契约。
2. `session` 负责执行上下文生命周期。
3. `board` 负责板级硬件描述加载。
4. `engine` 负责虚拟时间和离散事件调度。
5. `devices` 负责总线与设备语义。
6. `diagnosis` 负责事件、事实、解释链。
7. `scenario` 负责 YAML 场景、刺激与断言。
8. `artifacts` 负责状态查询、日志和复现包。

## 6. 阅读顺序

如果你是第一次进入项目，按下面顺序读：

1. 先读本文件。
2. 读 `01_api_module_report.md` 和 `04_engine_module_report.md`，理解系统骨架。
3. 读 `05_devices_module_report.md` 和 `06_diagnosis_module_report.md`，理解核心差异化能力。
4. 读 `07_scenario_module_report.md` 和 `08_artifacts_module_report.md`，理解闭环与回归。
5. 最后读 `02_session_module_report.md` 和 `03_board_module_report.md`，补全上下文与配置输入。

## 7. 各模块报告索引

1. `01_api_module_report.md`
2. `02_session_module_report.md`
3. `03_board_module_report.md`
4. `04_engine_module_report.md`
5. `05_devices_module_report.md`
6. `06_diagnosis_module_report.md`
7. `07_scenario_module_report.md`
8. `08_artifacts_module_report.md`

## 8. 你在实现时必须维持的硬约束

1. `devices` 不直接生成人类解释文本，只输出事件和事实原料。
2. `diagnosis` 不直接依赖私有后端格式，只消费统一事件或诊断事实。
3. `artifacts` 的所有输出都必须绑定 `session_id`，未来要可平滑演进到 `run_id`。
4. `scenario` 只通过公开服务接口控制执行，不应旁路核心状态。
5. 所有 API 错误都必须包含稳定 `error_code`，并尽量提供 `explain/observations/next_actions`。

## 9. 并行开发总规则

如果多个 AI agent 分时或并行实现模块，必须遵守下面规则：

1. 每个 agent 只能实现自己负责模块的内部逻辑，不得顺手改别的模块契约。
2. 跨模块交互只能通过各模块报告中声明的“公开接口要求”，不能直接读对方内部状态结构。
3. 如果某模块尚未实现，调用方必须先写清楚 stub interface 或 protocol，不得自行发明隐式字段。
4. 所有跨模块数据对象都必须是可序列化的稳定结构，优先使用 Pydantic 模型或等价 dataclass。
5. 未经显式升级决策，不允许把 `session` 擅自拆成 `session/run/artifact` 三层。
6. 未经显式升级决策，不允许把当前 Mode A 代码偷偷耦合到 Renode/QEMU。
7. 任何模块都不得越级依赖 `diagnosis` 规则表或 `devices` 私有运行时。

## 10. 模块接缝统一规则

所有模块在实现时都必须满足：

1. 输入对象名称稳定，字段语义稳定，字段缺省值可解释。
2. 输出对象不得混入仅供调试使用的临时字段。
3. 错误必须区分“平台内部错误”和“被测对象行为结果”。
4. 时间字段统一使用 `ns` 作为内部单位。
5. 标识字段统一使用 `session_id`、`request_id`、`event_id`、`fact_id`。
6. 所有事件、事实、解释都必须能追溯来源链。

## 11. 推荐并行批次

第一批可并行：

1. `api`
2. `session`
3. `board`

第二批可并行：

1. `engine`
2. `devices`

第三批可并行：

1. `diagnosis`
2. `scenario`
3. `artifacts`

## 12. 模块 ownership 规则

1. `api` 拥有外部 HTTP 契约、请求响应模型、错误映射。
2. `session` 拥有会话元数据和运行时上下文注册。
3. `board` 拥有板级 schema、校验、归一化结构。
4. `engine` 拥有虚拟时钟、事件队列、执行编排。
5. `devices` 拥有总线语义和设备插件运行时。
6. `diagnosis` 拥有事件到事实到解释的规则链。
7. `scenario` 拥有 YAML DSL、时间线计划和断言。
8. `artifacts` 拥有状态查询、事件落盘和复现包结构。

## 13. 如果你要开始编码

默认从下面顺序推进：

1. `api`
2. `session`
3. `board`
4. `engine`
5. `devices`
6. `diagnosis`
7. `scenario`
8. `artifacts`

## 14. 结论

把本目录视为“按模块拆解后的执行蓝图”。
