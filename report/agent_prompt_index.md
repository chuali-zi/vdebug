# Agent/AI Prompt Index

版本：v1.1  
日期：2026-04-07  
定位：给 agent / AI 使用的项目总入口与报告索引，不是给人类做完整架构评审用的正文。

---

## 1. 这是什么项目

这是一个帮助 agent 自主调试嵌入式设备的软件工具。  
它不追求一开始就做成“全能仿真器”，而是优先做成一个完整、可实施、可调试、可回归的系统：

1. 用虚拟环境模拟嵌入式设备的部分物理、电气、时序反应。
2. 让 agent 能通过统一接口执行调试动作、注入场景、读取状态、获取解释。
3. 重点排查嵌入式程序的软件侧问题，尤其是配置错误、时序错误、总线错误、初始化顺序错误。
4. 输出的不只是“失败了”，还要给出证据绑定的解释，帮助 agent 缩小问题范围。
5. 当前阶段优先保证 MVP 能闭环跑通，并为未来接入更强后端和更多设备模型留接口。

一句话定义：

> 这是一个面向 agent 的、可脚本化的、可解释的嵌入式虚拟调试平台。

---

## 2. AI 工作总原则

如果你是第一次进入本项目，默认遵守以下原则：

1. 先看 MVP，再看完整版架构。
2. 默认以可实施性优先，不以理论完整性优先。
3. 默认当前目标是做完整闭环，不是做大全。
4. 默认优先支持 Mode A（Device-Simulation），不默认做真实固件在环。
5. 默认技术路线以 Python + FastAPI + Pydantic + YAML + 文件存储为主。
6. 默认先解决 GPIO / UART / I2C。
7. 所有解释必须绑定证据，不能输出“玄学提示”。
8. 所有扩展设计都必须建立在不破坏 MVP 简洁性的前提下。

---

## 3. 文档优先级

当多份报告出现信息重叠时，按下面顺序理解和执行：

1. `architecture_mvp_simplified.md`
2. `architecture_report_v2_new.md`
3. `architecture_modules_map_new.md`
4. `architecture_report_new.md`
5. `deep-research-report (2).md`

解释：

1. `architecture_mvp_simplified.md` 是当前实施基线。
2. `architecture_report_v2_new.md` 是长期架构的修订版主文档。
3. `architecture_modules_map_new.md` 是模块落地映射图。
4. `architecture_report_new.md` 适合补充原始设计意图。
5. `deep-research-report (2).md` 主要解决“为什么这样做”，不是当前编码实现的主依据。

---

## 4. 当前代码状态

当前仓库已经不是纯文档状态，而是“文档 + 可继续协作的代码骨架”：

1. `src/lot/` 已存在 8 个 MVP 模块骨架。
2. `contracts` 层已经落下稳定数据模型、协议接口和错误对象。
3. FastAPI 主入口已经存在于 `src/lot/main.py`。
4. 模块装配已经存在于 `src/lot/bootstrap.py`。
5. API 主接缝已经存在于 `src/lot/api/routes.py` 和 `src/lot/api/facade.py`。
6. 当前大量业务逻辑仍保留为 `TODO`，这是刻意设计，不是遗漏。

这意味着：

1. 后续 agent 默认应在既有骨架内补实现。
2. 默认不应把项目当成空仓库再重新搭一版结构。
3. 默认不应轻易改动跨模块边界文件。

---

## 5. 快速阅读顺序

如果时间非常少，按这个顺序读：

1. 先读 `First read me.md`
2. 再读 `architecture_mvp_simplified.md`
3. 再读 `agent_module_arch_reports_20260407/SYSTEM_PROMPT_INDEX.md`
4. 最后按需查 `architecture_modules_map_new.md`

如果需要完整理解项目来源，再补：

5. `architecture_report_v2_new.md`
6. `architecture_report_new.md`
7. `deep-research-report (2).md`

---

## 6. 每份报告怎么用

### `First read me.md`

这是当前最实用的“上下文路由入口”。它回答：

1. 当前仓库已经落了什么骨架。
2. 现在到底做什么，不做什么。
3. 每类任务的最小读取集是什么。
4. 该先看哪些代码文件，不该通读哪些报告。

### `architecture_mvp_simplified.md`

这是当前最重要的架构基线。它回答：

1. 当前到底做什么，不做什么。
2. 当前推荐技术栈是什么。
3. 当前最小模块集合是什么。
4. 当前最小 API 是什么。
5. 当前最简数据模型是什么。
6. 当前阶段计划是什么。

### `agent_module_arch_reports_20260407/SYSTEM_PROMPT_INDEX.md`

这是 8 模块统一硬约束入口。它回答：

1. 当前骨架已经落在哪里。
2. 哪些跨模块接缝不能乱改。
3. 多 agent 并行开发时应该怎么对齐。

### `architecture_modules_map_new.md`

这是模块蓝图。它适合回答：

1. 模块怎么拆。
2. 模块之间怎么联动。
3. 哪些模块属于接入层、控制层、执行层、诊断层。
4. 实现优先级如何分批。

### `architecture_report_v2_new.md`

这是完整版修订主架构。它适合回答：

1. 长期系统边界是什么。
2. 为什么要区分 Mode A / Mode B。
3. 为什么解释链前面要加 Diagnostic Facts Layer。
4. 为什么长期数据模型要拆成 Session / Run / Artifact。
5. 未来怎样兼容 MCP。

### `architecture_report_new.md`

这是 v1 完整架构稿。它适合回答原始整体设计原则与早期对象模型设计。

### `deep-research-report (2).md`

这是项目背景研究与方案调研。它适合回答项目为什么成立，以及和行业路线相比的取舍依据。

---

## 7. 当前默认实现结论

在没有新指令覆盖的情况下，agent 默认按以下结论行动：

1. 当前项目目标是先完成 MVP 闭环。
2. 当前主模式是 Mode A: Device-Simulation。
3. 当前主问题域是 GPIO、UART、I2C。
4. 当前主接口是 REST API。
5. 当前主输入是：
   - `board_profile.yaml`
   - 场景 DSL（YAML）
   - Agent 的 JSON 请求
6. 当前主输出是：
   - 状态
   - 事件
   - 诊断事实
   - 解释
   - 最小复现包
7. 当前解释机制必须满足：
   - 有证据
   - 有候选原因
   - 有下一步建议
   - 不能脱离事件乱猜
8. 当前代码状态必须理解为：
   - 边界已落地
   - 语义未完整
   - `TODO` 是主施工入口

---

## 8. 推荐的 AI 定位方式

当你需要定位内容时，直接按任务类型跳转：

1. 想知道“现在到底该做什么”  
   -> 看 `First read me.md` 和 `architecture_mvp_simplified.md`

2. 想知道“当前仓库已经落了什么代码骨架”  
   -> 看 `First read me.md` 第 5、6 节  
   -> 看 `src/lot/bootstrap.py` 和 `src/lot/contracts/`

3. 想知道“模块应该怎么拆”  
   -> 看 `architecture_modules_map_new.md`

4. 想知道“长期为什么这样设计”  
   -> 看 `architecture_report_v2_new.md`

5. 想知道“行业参考和路线依据”  
   -> 看 `deep-research-report (2).md`

---

## 9. 环境与启动

如果需要实际运行当前仓库，先看：

1. `ENVIRONMENT.md`
2. `requirements.txt`
3. `pyproject.toml`

启动脚本：

1. `scripts/run.ps1`
2. `scripts/run.sh`

应用入口：

1. `src/lot/main.py`

---

## 10. 未来扩展时的硬约束

未来可以扩展，但不要直接跳过 MVP。扩展顺序建议保持为：

1. 先把 MVP 做完整。
2. 再把 Session / Run / Artifact 从简化模型恢复出来。
3. 再加入 MCP 工具封装。
4. 再接 Renode。
5. 再考虑 QEMU。
6. 最后才考虑更重的电气、信号级后端。

禁止默认做的事：

1. 直接把项目扩成通用 MCU 全精度仿真器。
2. 在 MVP 阶段引入过多总线和器件。
3. 在没有证据模型前先做复杂 LLM 解释层。
4. 在没有闭环之前先追求花哨协议和复杂工程化外壳。

---

## 11. 给后续 Agent 的一句操作提示

如果你要继续推进这个项目，请先把 `First read me.md` 当作当前上下文入口，把 `architecture_mvp_simplified.md` 当作当前执行规范，把 `SYSTEM_PROMPT_INDEX.md` 当作跨模块硬约束，再按“先补 TODO、再谈扩展”的原则行动。
