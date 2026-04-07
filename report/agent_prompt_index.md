# Agent/AI Prompt Index

版本：v1.0  
日期：2026-04-06  
定位：给 agent / AI 使用的项目总入口与报告索引，不是给人类做完整架构评审用的正文。

---

## 1. 这是什么项目

这是一个**帮助 agent 自主调试嵌入式设备的软件工具**。  
它不追求一开始就做成“全能仿真器”，而是优先做成一个**完整、可实施、可调试、可回归**的系统：

1. 用虚拟环境模拟嵌入式设备的部分物理/电气/时序反应。
2. 让 agent 能通过统一接口执行调试动作、注入场景、读取状态、获取解释。
3. 重点排查**嵌入式程序的软件侧问题**，尤其是配置错误、时序错误、总线错误、初始化顺序错误。
4. 输出的不只是“失败了”，还要给出**证据绑定的解释**，帮助 agent 缩小问题范围。
5. 当前阶段优先保证 **MVP 能闭环跑通**，并为未来接入更强后端和更多设备模型留接口。

一句话定义：

> 这是一个面向 agent 的、可脚本化的、可解释的嵌入式虚拟调试平台。

---

## 2. AI 工作总原则

如果你是第一次进入本项目，默认遵守以下原则：

1. **先看 MVP，再看完整版架构。**
2. **默认以可实施性优先，不以理论完整性优先。**
3. **默认当前目标是做完整闭环，不是做大全。**
4. **默认优先支持 Mode A（Device-Simulation），不默认做真实固件在环。**
5. **默认技术路线以 Python + FastAPI + Pydantic + YAML + 文件存储为主。**
6. **默认先解决 GPIO / UART / I2C。**
7. **所有解释必须绑定证据，不能输出“玄学提示”。**
8. **所有扩展设计都必须建立在不破坏 MVP 简洁性的前提下。**

---

## 3. 文档优先级

当多份报告出现信息重叠时，按下面顺序理解和执行：

1. `architecture_mvp_simplified.md`
2. `architecture_report_v2_new.md`
3. `architecture_modules_map_new.md`
4. `architecture_report_new.md`
5. `deep-research-report (2).md`

解释：

1. `architecture_mvp_simplified.md` 是**当前实施基线**。
2. `architecture_report_v2_new.md` 是**长期架构的修订版主文档**。
3. `architecture_modules_map_new.md` 是**模块落地映射图**。
4. `architecture_report_new.md` 是 v1 基础版，适合补充原始设计意图。
5. `deep-research-report (2).md` 主要解决“为什么这样做”和“行业参考是什么”，不是当前编码实现的主依据。

---

## 4. 快速阅读顺序

如果时间非常少，按这个顺序读：

1. 先读 `architecture_mvp_simplified.md`
2. 再读 `architecture_report_v2_new.md`
3. 最后按需查 `architecture_modules_map_new.md`

如果需要完整理解项目来源，再补：

4. `architecture_report_new.md`
5. `deep-research-report (2).md`

---

## 5. 每份报告怎么用

### `architecture_mvp_simplified.md`

这是最重要的文件。它回答：

1. 当前到底做什么，不做什么。
2. 当前推荐技术栈是什么。
3. 当前最小模块集合是什么。
4. 当前最小 API 是什么。
5. 当前最简数据模型是什么。
6. 当前适合大一新生落地的阶段计划是什么。

默认结论：

1. 只做 Mode A。
2. 不接 Renode/QEMU。
3. 不做 MCP。
4. 不做 gRPC/WebSocket/SSE。
5. 只做 8 个模块。
6. Session 暂时等于一次执行。

如果 agent 要开始写代码、拆目录、定接口、安排开发顺序，优先看这份。

### `architecture_report_v2_new.md`

这是完整版修订主架构。它适合回答：

1. 长期系统边界是什么。
2. 为什么要区分 Mode A / Mode B。
3. 为什么解释链前面要加 Diagnostic Facts Layer。
4. 为什么长期数据模型要拆成 Session / Run / Artifact。
5. 未来怎样兼容 MCP。

如果 agent 正在做架构升级、准备从 MVP 走向中期版本，优先看这份。

### `architecture_modules_map_new.md`

这是模块蓝图。它适合回答：

1. 24 个实现模块分别是什么。
2. 模块之间如何联动。
3. 哪些模块属于接入层、控制层、执行层、诊断层。
4. 实现优先级如何分批。

如果 agent 需要拆任务、分模块施工、梳理依赖关系，优先看这份。

### `architecture_report_new.md`

这是 v1 完整架构稿。它适合回答：

1. 原始整体设计原则是什么。
2. 标准对象模型和 API 设计最初是什么样。
3. 可观测性、确定性、回放、安全、SLO 的初版想法是什么。

如果 agent 需要补足“为什么这个概念一开始会被引入”，可以回看这份。

### `deep-research-report (2).md`

这是项目背景研究与方案调研。它适合回答：

1. 项目为什么成立。
2. 和 Renode / QEMU / Wokwi / Zephyr native_sim 这些路线相比，本项目的差异点是什么。
3. 哪些方向适合 MVP，哪些方向明显过重。
4. 为什么“可解释反馈 + 场景回放 + agent 友好接口”是合理切入点。

如果 agent 需要写立项说明、设计依据、路线对比、可行性分析，优先看这份。

---

## 6. 当前默认实现结论

在没有新指令覆盖的情况下，agent 默认按以下结论行动：

1. 当前项目目标是先完成 **MVP 闭环**。
2. 当前主模式是 **Mode A: Device-Simulation**。
3. 当前主要问题域是：
   - GPIO 配置错误
   - UART 配置错误
   - I2C 地址/上拉/超时/占线问题
   - 初始化顺序和简单时序问题
4. 当前主接口是 **REST API**。
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

---

## 7. 推荐的 AI 定位方式

当你需要定位内容时，直接按任务类型跳转：

1. 想知道“现在到底该做什么”  
   -> 看 `architecture_mvp_simplified.md`

2. 想知道“长期为什么这样设计”  
   -> 看 `architecture_report_v2_new.md`

3. 想知道“模块应该怎么拆”  
   -> 看 `architecture_modules_map_new.md`

4. 想知道“原始完整架构长什么样”  
   -> 看 `architecture_report_new.md`

5. 想知道“行业参考和路线依据”  
   -> 看 `deep-research-report (2).md`
---

## 8. 未来扩展时的硬约束

未来可以扩展，但不要直接跳过 MVP。扩展顺序建议保持为：

1. 先把 MVP 做完整。
2. 再把 Session / Run / Artifact 从简化模型恢复出来。
3. 再加入 MCP 工具封装。
4. 再接 Renode。
5. 再考虑 QEMU。
6. 最后才考虑更重的电气/信号级后端。

禁止默认做的事：

1. 直接把项目扩成通用 MCU 全精度仿真器。
2. 在 MVP 阶段引入过多总线和器件。
3. 在没有证据模型前先做复杂 LLM 解释层。
4. 在没有闭环之前先追求花哨协议和复杂工程化外壳。

---

## 9. 给后续 Agent 的一句操作提示

如果你要继续推进这个项目，请先把 `architecture_mvp_simplified.md` 当作当前执行规范，把 `architecture_report_v2_new.md` 当作未来升级方向，把 `architecture_modules_map_new.md` 当作任务拆分地图，再按“先闭环、再扩展”的原则行动。

