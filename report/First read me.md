# 架构初始索引（按需读取版）

版本：v0.1  
日期：2026-04-07  
目的：给后续 agent 做“上下文路由”，避免每次编码前重读全部架构文档。

---

## 1. 使用规则

后续 agent 默认按下面顺序工作：

1. 先读本文件。
2. 先判断当前任务属于哪个模块或哪类问题。
3. 只读本文件指定的最小文档集合。
4. 只有在当前文档不能回答问题时，才升级去读下一层文档。

默认禁止的低效做法：

1. 一上来通读 `report/` 全部架构文件。
2. 做单一 MVP 模块时同时读取 v1、v2、research 全文。
3. 在没有升级需求时，把 Mode B、MCP、Renode、QEMU 内容当成当前实现基线。

---

## 2. 文档优先级

如果多份文档对同一问题有重复描述，按下面优先级理解：

1. `report/architecture_mvp_simplified.md`
2. `report/architecture_report_v2_new.md`
3. `report/architecture_modules_map_new.md`
4. `report/agent_module_arch_reports_20260407/SYSTEM_PROMPT_INDEX.md`
5. `report/agent_module_arch_reports_20260407/01_api_module_report.md` 到 `08_artifacts_module_report.md`
6. `report/architecture_report_new.md`
7. `report/deep-research-report (2).md`
8. `report/agent_prompt_index.md`

解释：

1. `architecture_mvp_simplified.md` 是当前实施基线。
2. `architecture_report_v2_new.md` 是未来升级方向，不是默认全量实现要求。
3. `architecture_modules_map_new.md` 用于拆任务、定边界、查依赖。
4. 8 份模块报告用于写具体模块代码时收窄上下文。
5. `architecture_report_new.md` 和 `deep-research-report (2).md` 主要用于补“为什么这样设计”。

---

## 3. 已读文件清单

本次已通读或通读式梳理的架构文件范围：

1. `report/architecture_mvp_simplified.md`
2. `report/architecture_report_v2_new.md`
3. `report/architecture_modules_map_new.md`
4. `report/architecture_report_new.md`
5. `report/deep-research-report (2).md`
6. `report/agent_prompt_index.md`
7. `report/agent_module_arch_reports_20260407/SYSTEM_PROMPT_INDEX.md`
8. `report/agent_module_arch_reports_20260407/01_api_module_report.md`
9. `report/agent_module_arch_reports_20260407/02_session_module_report.md`
10. `report/agent_module_arch_reports_20260407/03_board_module_report.md`
11. `report/agent_module_arch_reports_20260407/04_engine_module_report.md`
12. `report/agent_module_arch_reports_20260407/05_devices_module_report.md`
13. `report/agent_module_arch_reports_20260407/06_diagnosis_module_report.md`
14. `report/agent_module_arch_reports_20260407/07_scenario_module_report.md`
15. `report/agent_module_arch_reports_20260407/08_artifacts_module_report.md`

---

## 4. 当前实施基线

当前默认基线，不要在没有新指令时偏离：

1. 只做 `Mode A: Device-Simulation`。
2. 技术路线默认是 `Python + FastAPI + Pydantic + YAML + 文件存储`。
3. 当前 MVP 只保留 8 个模块：`api / session / board / engine / devices / diagnosis / scenario / artifacts`。
4. 当前主问题域是 `GPIO / UART / I2C`。
5. 当前解释链必须是 `事件 -> 诊断事实 -> 解释`，不能直接从原始事件生成玄学结论。
6. 当前不默认做 `MCP / Renode / QEMU / WebSocket / SSE / gRPC`。
7. 当前 `Session = 一次执行`，还没有正式拆成 `Session / Run / Artifact` 三层。

---

## 5. 当前仓库与规划目录的关系

当前仓库状态：

1. `src/` 目录目前为空。
2. 架构文档里的“建议目录结构”还没有完全落地成源码。

后续编码时建议把 8 个 MVP 模块落到：

1. `src/api`
2. `src/session`
3. `src/board`
4. `src/engine`
5. `src/devices`
6. `src/diagnosis`
7. `src/scenario`
8. `src/artifacts`

说明：

1. `architecture_mvp_simplified.md` 第 10 节给的是一个示例目录结构，语义可保留。
2. 具体仓库落地时，优先对齐当前仓库的 `src/` 目录，而不是机械照抄报告里的 `lot/` 样例根路径。

---

## 6. 文件定位总表

### 6.1 主文档

| 文件 | 定位 | 什么时候读 | 不需要读的时候 |
|---|---|---|---|
| `report/architecture_mvp_simplified.md` | 当前编码基线 | 任何 MVP 编码任务开始前 | 几乎没有 |
| `report/architecture_report_v2_new.md` | 长期升级版主架构 | 需要理解 `Mode A/B`、`Diagnostic Facts Layer`、`Session/Run/Artifact`、未来 MCP 时 | 纯 MVP 单模块开发 |
| `report/architecture_modules_map_new.md` | 模块依赖和批次蓝图 | 需要拆任务、定依赖、并行开发时 | 单文件实现细节 |
| `report/architecture_report_new.md` | v1 原始完整稿 | 需要补原始设计意图时 | 已有更高优先级文档可回答时 |
| `report/deep-research-report (2).md` | 背景研究和路线比较 | 写设计依据、路线比较、立项材料时 | 日常编码 |

### 6.2 Agent 索引与模块报告

| 文件 | 定位 | 什么时候读 | 不需要读的时候 |
|---|---|---|---|
| `report/agent_module_arch_reports_20260407/SYSTEM_PROMPT_INDEX.md` | 8 模块系统级硬约束 | 进入模块编码前，先对齐默认规则 | 已经明确当前任务的模块边界时 |
| `report/agent_module_arch_reports_20260407/01_api_module_report.md` | API 模块细化约束 | 写接口、错误码、请求响应模型时 | 非 API 任务 |
| `report/agent_module_arch_reports_20260407/02_session_module_report.md` | Session 模块细化约束 | 写会话生命周期、runtime container 时 | 非 session 任务 |
| `report/agent_module_arch_reports_20260407/03_board_module_report.md` | Board 模块细化约束 | 写 board_profile 解析与校验时 | 非 board 任务 |
| `report/agent_module_arch_reports_20260407/04_engine_module_report.md` | Engine 模块细化约束 | 写虚拟时钟、调度器、step 语义时 | 非 engine 任务 |
| `report/agent_module_arch_reports_20260407/05_devices_module_report.md` | Devices 模块细化约束 | 写 GPIO/UART/I2C 插件和故障注入时 | 非 devices 任务 |
| `report/agent_module_arch_reports_20260407/06_diagnosis_module_report.md` | Diagnosis 模块细化约束 | 写 facts / rules / explainer 时 | 非 diagnosis 任务 |
| `report/agent_module_arch_reports_20260407/07_scenario_module_report.md` | Scenario 模块细化约束 | 写 DSL、planner、runner、assertions 时 | 非 scenario 任务 |
| `report/agent_module_arch_reports_20260407/08_artifacts_module_report.md` | Artifacts 模块细化约束 | 写 state view、NDJSON 落盘、repro bundle 时 | 非 artifacts 任务 |

---

## 7. 最小读取集

### 7.1 先判断任务属于哪一类

如果任务是下面类型，直接读对应最小集合：

1. “我要知道现在到底做什么，不做什么”
   - 读 `report/architecture_mvp_simplified.md`：
     - 第 1 节 `MVP 范围约束`，起始行 27
     - 第 2 节 `推荐技术栈`，起始行 49
     - 第 3 节 `模块设计（8 个模块）`，起始行 62

2. “我要拆模块、拆批次、看依赖”
   - 读 `report/architecture_modules_map_new.md`：
     - 第 2 节 `实现模块总览`，起始行 24
     - 第 4 节 `核心联动关系`，起始行 98
     - 第 7 节 `模块依赖约束`，起始行 159
     - 第 8 节 `建议实现优先级`，起始行 169

3. “我要知道长期为什么这样设计”
   - 读 `report/architecture_report_v2_new.md`：
     - 第 2 节 `两种运行模式`，起始行 45
     - 第 4 节 `诊断事实层`，起始行 111
     - 第 5 节 `Session / Run / Artifact`，起始行 143

4. “我要写设计依据、路线比较”
   - 读 `report/deep-research-report (2).md`
   - 再读 `report/architecture_report_new.md` 第 2 节 `架构设计原则`，起始行 35

### 7.2 单模块编码最小读取集

#### `api`

必读：

1. `report/architecture_mvp_simplified.md`
   - 第 5 节 `API 设计`，起始行 181
   - 第 6 节 `响应格式`，起始行 198
   - 第 10 节 `建议目录结构`，起始行 306
2. `report/agent_module_arch_reports_20260407/01_api_module_report.md`
   - 第 4 节 `对外接口`，起始行 29
   - 第 7 节 `关键数据契约`，起始行 90
   - 第 10 节 `硬约束`，起始行 146
   - 第 11 节 `公开接口要求`，起始行 154

按需补充：

1. `report/architecture_report_v2_new.md`
   - 第 7 节 `API 设计（v2 修订）`，起始行 217

#### `session`

必读：

1. `report/architecture_mvp_simplified.md`
   - 第 4.1 节 `Session`，起始行 132
   - 第 10 节 `建议目录结构`，起始行 306
2. `report/agent_module_arch_reports_20260407/02_session_module_report.md`
   - 第 4 节 `核心数据模型`，起始行 27
   - 第 6 节 `状态机`，起始行 55
   - 第 7 节 `核心工作流`，起始行 63
   - 第 9 节 `硬约束`，起始行 92
   - 第 10 节 `公开接口要求`，起始行 99

按需补充：

1. `report/architecture_report_v2_new.md`
   - 第 5 节 `数据模型重构：Session / Run / Artifact`，起始行 143

#### `board`

必读：

1. `report/architecture_mvp_simplified.md`
   - 第 7 节 `board_profile.yaml`，起始行 226
2. `report/architecture_report_v2_new.md`
   - 第 6 节 `板级硬件抽象`，起始行 171
3. `report/agent_module_arch_reports_20260407/03_board_module_report.md`
   - 第 4 节 `输入与输出`，起始行 25
   - 第 5 节 `核心数据模型`，起始行 38
   - 第 7 节 `关键校验规则`，起始行 57
   - 第 10 节 `公开接口要求`，起始行 79

#### `engine`

必读：

1. `report/architecture_mvp_simplified.md`
   - 第 3.1 节 `模块联动`，起始行 77
   - 第 4.2 节 `SimEvent`，起始行 144
   - 第 10 节 `建议目录结构`，起始行 306
   - 第 11 节 `实施计划`，起始行 349
2. `report/architecture_modules_map_new.md`
   - 第 4 节 `核心联动关系`，起始行 98
   - 第 5.1 节 `Mode A`，起始行 118
   - 第 7 节 `模块依赖约束`，起始行 159
3. `report/agent_module_arch_reports_20260407/04_engine_module_report.md`
   - 第 5 节 `核心数据模型`，起始行 41
   - 第 7 节 `调度规则`，起始行 76
   - 第 8 节 `核心工作流`，起始行 83
   - 第 10 节 `硬约束`，起始行 111
   - 第 11 节 `公开接口要求`，起始行 119

按需补充：

1. `report/architecture_report_v2_new.md`
   - 第 3 节 `Core 与 Backend 的职责边界`，起始行 89

#### `devices`

必读：

1. `report/architecture_mvp_simplified.md`
   - 第 1 节 `MVP 范围约束`，起始行 27
   - 第 3 节 `模块设计（8 个模块）`，起始行 62
   - 第 7 节 `board_profile.yaml`，起始行 226
   - 第 9 节 `解释规则`，起始行 275
2. `report/agent_module_arch_reports_20260407/05_devices_module_report.md`
   - 第 5 节 `插件抽象建议`，起始行 39
   - 第 6 节 `子架构拆分`，起始行 51
   - 第 7 节 `与其他模块的协作`，起始行 72
   - 第 8 节 `硬约束`，起始行 89
   - 第 9 节 `公开接口要求`，起始行 96
   - 第 11 节 `故障注入设计`，起始行 118

按需补充：

1. `report/architecture_report_v2_new.md`
   - 第 4.3 节 `事实样例`，起始行 120
   - 第 6.2 节 `board_profile.yaml（示例）`，起始行 176

#### `diagnosis`

必读：

1. `report/architecture_report_v2_new.md`
   - 第 4 节 `关键新增：诊断事实层`，起始行 111
2. `report/architecture_mvp_simplified.md`
   - 第 4.3 节 `DiagnosticFact`，起始行 157
   - 第 4.4 节 `Explanation`，起始行 168
   - 第 9 节 `解释规则`，起始行 275
3. `report/agent_module_arch_reports_20260407/06_diagnosis_module_report.md`
   - 第 3 节 `诊断流水线`，起始行 23
   - 第 4 节 `核心数据模型`，起始行 29
   - 第 6 节 `事实提取设计`，起始行 57
   - 第 7 节 `规则层设计`，起始行 66
   - 第 9 节 `硬约束`，起始行 87
   - 第 10 节 `公开接口要求`，起始行 94

#### `scenario`

必读：

1. `report/architecture_mvp_simplified.md`
   - 第 8 节 `场景 DSL`，起始行 248
2. `report/architecture_report_v2_new.md`
   - 第 8 节 `场景 DSL v2`，起始行 246
3. `report/agent_module_arch_reports_20260407/07_scenario_module_report.md`
   - 第 4 节 `输入与输出`，起始行 26
   - 第 5 节 `DSL 结构`，起始行 40
   - 第 7 节 `核心工作流`，起始行 56
   - 第 8 节 `断言类型建议`，起始行 66
   - 第 10 节 `硬约束`，起始行 87
   - 第 11 节 `公开接口要求`，起始行 94

#### `artifacts`

必读：

1. `report/architecture_report_v2_new.md`
   - 第 5.3 节 `最小复现包`，起始行 159
2. `report/architecture_mvp_simplified.md`
   - 第 6 节 `响应格式`，起始行 198
   - 第 10 节 `建议目录结构`，起始行 306
3. `report/agent_module_arch_reports_20260407/08_artifacts_module_report.md`
   - 第 4 节 `输入与输出`，起始行 26
   - 第 5 节 `推荐工件类型`，起始行 42
   - 第 7 节 `状态查询设计`，起始行 58
   - 第 8 节 `持久化策略`，起始行 68
   - 第 10 节 `硬约束`，起始行 91
   - 第 11 节 `公开接口要求`，起始行 98

---

## 8. 跨模块问题路由

如果任务不是“单模块编码”，按下面跳转：

1. “怎么拆分并行开发批次”
   - 读 `report/architecture_modules_map_new.md` 第 8 节，起始行 169
   - 读 `report/agent_module_arch_reports_20260407/SYSTEM_PROMPT_INDEX.md`
     - 第 9 节 `并行开发总规则`，起始行 95
     - 第 11 节 `推荐并行批次`，起始行 118
     - 第 12 节 `模块 ownership 规则`，起始行 137

2. “如何维持统一错误模型、统一响应体”
   - 读 `report/architecture_mvp_simplified.md` 第 6 节，起始行 198
   - 读 `report/agent_module_arch_reports_20260407/01_api_module_report.md` 第 4 节和第 7 节

3. “如何维持统一事件模型”
   - 读 `report/architecture_mvp_simplified.md` 第 4.2 节，起始行 144
   - 读 `report/architecture_report_new.md` 第 5.3 节，起始行 214
   - 读 `report/agent_module_arch_reports_20260407/04_engine_module_report.md` 第 5 节，起始行 41

4. “如何维持解释必须绑定证据”
   - 读 `report/architecture_report_v2_new.md` 第 4 节，起始行 111
   - 读 `report/architecture_report_new.md` 第 8.2 节，起始行 316
   - 读 `report/agent_module_arch_reports_20260407/06_diagnosis_module_report.md` 第 7 节和第 9 节

5. “最小复现包应包含什么”
   - 读 `report/architecture_report_v2_new.md` 第 5.3 节，起始行 159
   - 读 `report/agent_module_arch_reports_20260407/08_artifacts_module_report.md` 第 5 节和第 11 节

6. “未来怎样从 MVP 演进到长期架构”
   - 读 `report/architecture_mvp_simplified.md` 第 12 节，起始行 388
   - 读 `report/architecture_report_v2_new.md` 第 11 节，起始行 330
   - 读 `report/architecture_modules_map_new.md` 第 8 节，起始行 169

---

## 9. 默认不读清单

在下面场景里，不需要读这些文件：

1. 做单一 MVP 模块编码时，不需要读 `report/deep-research-report (2).md`。
2. 没有升级到 `Mode B` 的需求时，不需要细读 `report/architecture_report_v2_new.md` 第 2.2、10、11 节。
3. 只改单模块内部实现时，不需要重读 `report/architecture_report_new.md` 全文。
4. 只写 `api/session/board/engine/devices/diagnosis/scenario/artifacts` 之一时，不需要同时读其他 7 份模块报告。

---

## 10. 后续 Agent 的默认操作提示

如果你是后续进入仓库的 agent，默认这样执行：

1. 先读本文件，不要先读全部架构文档。
2. 如果任务落在某个 MVP 模块，只读该模块的“最小读取集”。
3. 如果任务涉及跨模块边界，再补 `architecture_modules_map_new.md` 和 `SYSTEM_PROMPT_INDEX.md`。
4. 只有当你发现 MVP 文档回答不了当前问题时，才升级去读 `architecture_report_v2_new.md`。
5. 只有当你在写设计依据、路线比较或升级方案时，才去读 `architecture_report_new.md` 和 `deep-research-report (2).md`。

---

## 11. 一句话结论

这份索引的目标不是替代架构正文，而是把架构正文变成“可按任务跳读”的上下文路由层：默认以 `architecture_mvp_simplified.md` 为执行基线，以 8 份模块报告为编码入口，以 `architecture_report_v2_new.md` 为升级补充，而不是每次从头通读全部报告。
