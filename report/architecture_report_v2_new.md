# 面向调试 Agent 的嵌入式模拟虚拟环境
## 详细架构设计报告（第二稿，评审反馈修订版）

版本：v2.0（Review-Driven）  
日期：2026-04-06  
修订依据：用户架构评审反馈 + `deep-research-report (2).md` + `architecture_report_new.md`

---

## 0. 本次修订摘要（相对 v1）

本版针对评审意见做了 8 项关键修订：

1. 明确 `host-native` 为**协议级仿真**，不是固件级指令仿真。  
2. 明确系统双运行模式：`Device-Simulation` 与 `Firmware-in-the-Loop`。  
3. 重定义 Simulation Core：区分“强控制内核”与“编排控制平面”两种角色。  
4. 在 Explanation Engine 前新增 `Diagnostic Facts Layer`（诊断事实层）。  
5. 数据模型新增 `Run/Execution`，拆分 Session 与一次执行。  
6. 场景 DSL 拆成 `setup/stimulus/assertions` 三段。  
7. SLO 改为分层指标：Control Plane / Host-native / Heavy Backend。  
8. 增补 MCP 工具协议兼容策略（可直接作为 MCP Server）。

---

## 1. 系统定位与边界（重新锚定）

### 1.1 系统定位
本系统首先是“面向 Agent 的可解释调试基础设施”，不是“通用全精度 MCU/SoC 仿真器”。

### 1.2 MVP 只解决的问题

1. 配置类问题（GPIO/UART/I2C/SPI/ADC 误配）。  
2. 时序类问题（超时、竞争、初始化顺序、RTOS 调度表征）。  
3. 可复现与可回归（场景回放、最小复现包、CI）。  
4. 证据绑定解释（不是黑盒猜测）。

### 1.3 MVP 不解决的问题

1. 通用 MCU 指令级高保真无修改全覆盖。  
2. 大规模寄存器级精确外设模型库。  
3. 默认 SPICE/周期级联合仿真（后续按需插件化）。

---

## 2. 两种运行模式（必须显式区分）

### 2.1 Mode A: Device-Simulation（设备模拟模式）

定义：不加载真实固件，Agent 或场景直接驱动总线/设备语义命令。  
目标：快速验证协议、配置、故障注入与解释链路。

输入：

1. `board_profile.yaml`  
2. 场景 DSL  
3. 命令流（如 `i2c.transact`、`gpio.set`）

输出：

1. 结构化事件  
2. 诊断事实  
3. 解释与建议

### 2.2 Mode B: Firmware-in-the-Loop（固件在环模式）

定义：加载固件并推进虚拟时间，固件自行操作外设；平台注入外部刺激并观测。  
目标：定位真实固件逻辑路径中的配置/时序问题。

输入：

1. 固件镜像（ELF/HEX/后端可支持格式）  
2. `board_profile.yaml`  
3. 场景 DSL（刺激与断言）

输出：

1. 高层事件序列  
2. 证据绑定解释  
3. 可复现包

### 2.3 文档约束语句（防歧义）

1. `host-native` 默认归属 Mode A（协议级仿真）。  
2. `Renode/QEMU` 主要承载 Mode B（固件在环）。  
3. API 必须返回 `execution_mode`，避免调用方误判执行语义。

---

## 3. Core 与 Backend 的职责边界（修订重点）

### 3.1 分层定义

1. `Control Core`（统一控制平面）：会话、运行、命令编排、事件归一化、工件管理。  
2. `Execution Engine`（执行引擎）：
   - Host-native: 本系统自带离散事件引擎（强控制）。
   - Renode/QEMU: 后端自带执行机制（弱控制，强编排）。

### 3.2 边界规则

1. 对 Host-native：平台掌控主时间轴与事件队列。  
2. 对 Renode/QEMU：平台不强行接管底层调度，仅通过 adapter 做控制与抽象。  
3. 所有后端都必须转换到统一事件模型后再进入解释链。

### 3.3 统一调用语义

1. `step` 对 Host-native 为真实离散推进。  
2. `step` 对 Heavy Backend 为“后端步进请求 + 结果拉取”，语义保持一致但性能承诺分层。

---

## 4. 关键新增：诊断事实层（Diagnostic Facts Layer）

### 4.1 原因
解释规则不能直接绑定原始事件，否则事件格式调整会导致规则脆弱。

### 4.2 新流水线

`Raw Events -> Feature Extractors -> Diagnostic Facts -> Explanation Rules -> Hints`

### 4.3 事实样例

1. `bus_stuck_low(bus=i2c0,line=sda,duration_ms=12.3)`  
2. `repeated_nack(bus=i2c0,addr=0x48,count=3)`  
3. `spi_mode_mismatch(bus=spi0,expected=0,observed=3)`  
4. `gpio_direction_conflict(pin=PA3,expected=out,actual=in)`

### 4.4 解释输出规范（保留并增强）

1. `hypothesis[]`（候选原因列表，按证据权重排序）  
2. `confidence`（每候选独立评分）  
3. `observations`（引用事实 ID）  
4. `next_actions`（可执行动作）  
5. `uncertainty_note`（置信度低时强制输出）

### 4.5 Explanation Engine 与 LLM Agent 分工

1. Engine（MVP）：模式匹配、证据聚合、候选生成。  
2. LLM Agent：结合上下文做最终调试策略推理。  
3. 规则引擎不替代 LLM，而是为 LLM 提供“结构化高质量证据”。

---

## 5. 数据模型重构：Session / Run / Artifact

### 5.1 对象层级

1. `Session`：长期上下文容器（profile、backend、schema版本、权限）。  
2. `Run`（Execution）：一次具体执行（scene + seed + mode + firmware ref）。  
3. `Artifact`：挂在 Run 上的产物（trace、events、reports、repro bundle）。

### 5.2 生命周期

1. `create_session`  
2. `start_run`  
3. `step/run_until`  
4. `finalize_run`  
5. `export_artifacts(run_id)`

### 5.3 最小复现包（绑定 run_id）

1. `board_profile.yaml`  
2. `scene.yaml`  
3. `run_meta.json`（mode/backend/seed/schema versions）  
4. `firmware_manifest.json`（如有）  
5. `command_trace.ndjson`  
6. `event_stream.ndjson`  
7. `diagnostic_facts.ndjson`

---

## 6. 板级硬件抽象（新增 board_profile）

### 6.1 设计目标
给解释引擎和执行层提供统一硬件事实来源，避免“只知道总线，不知道板级连接语义”。

### 6.2 board_profile.yaml（示例）

```yaml
version: v1alpha1
board: custom_stm32f4_dev
mcu:
  family: stm32f4
  part: STM32F407VG
buses:
  i2c0:
    pins: { sda: PB7, scl: PB6 }
    electrical:
      pullup_ohm: 4700
      bus_cap_pf: 120
    devices:
      - addr_7bit: 0x48
        type: TMP102
        model: builtin/tmp102
  spi0:
    pins: { mosi: PA7, miso: PA6, sck: PA5, cs: PA4 }
    mode: 0
    devices:
      - type: W25Q64
        model: builtin/spi_flash
  uart0:
    pins: { tx: PA2, rx: PA3 }
    baud_default: 115200
power:
  vdd: 3.3
constraints:
  expected_boot_log_contains: "system init ok"
```

### 6.3 作用

1. 驱动设备实例化。  
2. 约束解释规则（例如 I2C 上拉、电容、目标器件存在性）。  
3. 作为复现包关键输入。

---

## 7. API 设计（v2 修订）

### 7.1 资源模型

1. `GET /v1/capabilities`  
2. `POST /v1/sessions`  
3. `POST /v1/sessions/{sid}/runs`  
4. `POST /v1/runs/{rid}/step`  
5. `POST /v1/runs/{rid}/run:until`  
6. `GET /v1/runs/{rid}/state`  
7. `GET /v1/runs/{rid}/events?since=...`  
8. `GET /v1/runs/{rid}/diagnostics`  
9. `POST /v1/runs/{rid}/artifacts:export`

### 7.2 I/O 命令约束

1. Mode A 允许直接总线事务命令。  
2. Mode B 对“直接总线写”默认受限（避免绕过固件执行语义），仅允许 fault injection / stimuli。  
3. 每次响应必须带 `mode`, `backend`, `schema_version`。

### 7.3 事件分级（吞吐量控制）

1. `L0_CRITICAL`：故障/超时/断言失败（必保留）。  
2. `L1_IMPORTANT`：事务摘要（默认保留）。  
3. `L2_VERBOSE`：字节级细节（按需采样）。  
4. `L3_TRACE`：超细粒度调试（默认关闭）。

---

## 8. 场景 DSL v2（测试导向）

### 8.1 三段结构

1. `setup`：板级/固件/初始变量。  
2. `stimulus`：时间线动作与故障注入。  
3. `assertions`：状态、事件、日志、时序断言。

### 8.2 示例

```yaml
version: v1alpha1
setup:
  mode: firmware_in_loop
  backend: renode
  board_profile: ./profiles/stm32f4_lab.yaml
  firmware:
    path: ./build/app.elf
    sha256: "..."
  seed: 42

stimulus:
  - at_ms: 0
    action: sensor.set
    params: { id: tmp102_0, temperature_c: 85 }
  - at_ms: 5
    action: fault.inject
    params: { kind: i2c_sda_stuck_low, bus: i2c0, duration_ms: 20 }

assertions:
  - within_ms: 50
    expect_event:
      type: BUS_TIMEOUT
      level: L0_CRITICAL
  - within_ms: 100
    expect_log_contains: "sensor init failed"
```

---

## 9. SLO 与性能承诺（分层修订）

### 9.1 Control Plane SLO（统一承诺）

1. `create_session` P95 < 300ms。  
2. `start_run` P95 < 500ms（不含重后端冷启动）。  
3. API 错误码稳定率 100%。

### 9.2 Host-native Backend SLO（强承诺）

1. 冷启动 P95 < 1s。  
2. `step(1ms)` P95 < 50ms。  
3. 10^5 事件场景 < 5s。  
4. 单实例内存 < 200MB。

### 9.3 Heavy Backend Baseline（Renode/QEMU）

1. 不承诺与 Host-native 同级时延。  
2. 承诺语义一致性与可复现性。  
3. 提供基线报告（环境、场景、事件量）用于性能对比。

---

## 10. MCP 兼容策略（新增）

### 10.1 目标
把平台直接包装为 MCP Server，供 Claude Code/Cursor 等通过 tools 调用。

### 10.2 对应关系

1. `capabilities` -> `tool: get_capabilities`  
2. `create_session/start_run` -> `tool: start_debug_run`  
3. `step/run_until` -> `tool: step_simulation` / `run_until`  
4. `events/diagnostics` -> `tool: get_diagnostics`  
5. `export_artifacts` -> `tool: export_repro_bundle`

### 10.3 契约要求

1. MCP tool 参数由 JSON Schema 描述。  
2. 错误模型与 REST 保持同一 `error_code` 集。  
3. 支持 stdio transport 作为本地默认通道。

---

## 11. 实施路线（v2 精化）

### 阶段 1（2~3 周）

1. Session/Run 数据模型与 API 骨架。  
2. 事件分级框架（L0~L3）。  
3. board_profile schema v1alpha1。

### 阶段 2（3~4 周）

1. Host-native Mode A：GPIO/UART/I2C/SPI 基础。  
2. Diagnostic Facts 提取器 v1。  
3. Explanation Engine（薄层）v1：候选生成 + 证据绑定。

### 阶段 3（4~6 周）

1. DSL 三段结构与断言执行器。  
2. 最小复现包导出（绑定 run）。  
3. CI 场景回放（场景即测试）。

### 阶段 4（6~10 周）

1. Renode Adapter（Mode B）。  
2. 语义一致性测试（Host-native vs Renode）。  
3. MCP server 封装与工具注册。

### 阶段 5（可选）

1. QEMU Adapter。  
2. ngspice/Verilator 关键插件路线验证。

---

## 12. 风险与门禁（修订后）

1. 风险：模式语义混淆（A/B 模式）。  
门禁：每次 run 必须显式 `mode`，响应必须回显。

2. 风险：解释层“玄学化”。  
门禁：无事实 ID 不得输出 hypothesis。

3. 风险：事件量爆炸拖垮 LLM。  
门禁：默认只上送 L0/L1 摘要给 Agent；L2/L3 按需请求。

4. 风险：后端接入后行为漂移。  
门禁：高层语义断言套件必须跨后端通过。

5. 风险：数据模型不可回溯。  
门禁：所有工件强制绑定 `run_id` 与版本元数据。

---

## 13. 最终结论（v2）

这套架构可以进入实现，但前提是按本版明确四个“不可再模糊”的设计决策：

1. `host-native` = 协议级仿真，不等同固件级执行。  
2. 运行模式分为 Device-Simulation 与 Firmware-in-the-Loop。  
3. 解释链必须经过 Diagnostic Facts Layer。  
4. 数据生命周期采用 Session -> Run -> Artifact。

在上述约束下，系统将具备：

1. 明确可执行边界（不会无限膨胀）。  
2. 可解释且可维护的诊断体系。  
3. 可复现、可回归、可被 Agent 标准化调用的工程能力。
