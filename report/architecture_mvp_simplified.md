# MVP 精简架构（基于原架构评审修订）

版本：v1.0  
日期：2026-04-06  
依据文件：
1. `deep-research-report (2).md`
2. `architecture_report_new.md`
3. `architecture_report_v2_new.md`
4. `architecture_modules_map_new.md`

---

## 0. 本文件定位

本文件**不替代**原有架构文档，而是从中提取一份**大一新生可实际落地的 MVP 精简方案**。

原架构的方向、原则、数据模型设计均保留，本文件做的是：

1. 将 24 个模块合并压缩为 **8 个实现模块**。
2. 明确 MVP 只做 **Mode A（Device-Simulation）**。
3. 明确推荐技术栈为 **Python**。
4. 将 Session/Run 合并为单层，降低数据模型复杂度。
5. 将 API 端点精简为最小可用集。

---

## 1. MVP 范围约束

### 做什么

1. Mode A（协议级设备模拟），不加载真实固件。
2. GPIO / UART / I2C 三种总线（SPI/ADC 作为 MVP 后的第一个扩展）。
3. 证据绑定的文本化解释输出。
4. YAML 场景回放与断言。
5. REST API 单入口（JSON）。

### 不做什么

1. Mode B（Firmware-in-the-Loop）。
2. Renode / QEMU 后端适配。
3. MCP 工具封装（MVP 后再加）。
4. gRPC / WebSocket / SSE。
5. 运行时 Schema 版本管理。
6. Telemetry / Audit。
7. 性能 SLO 硬指标（先跑通，再优化）。

---

## 2. 推荐技术栈

| 选项 | 推荐 | 理由 |
|---|---|---|
| 语言 | Python 3.11+ | 开发速度快，生态好，适合大一新生 |
| Web 框架 | FastAPI | 自带 OpenAPI 文档生成，JSON Schema 校验，async 支持 |
| 数据校验 | Pydantic v2 | FastAPI 原生集成，定义请求/响应模型即校验 |
| 场景解析 | PyYAML | 轻量，直接解析 YAML DSL |
| 测试 | pytest | Python 标准测试框架 |
| 存储 | 文件系统（JSON/NDJSON） | MVP 不需要数据库 |

---

## 3. 模块设计（8 个模块）

原 24 模块 → 8 模块的映射关系：

| MVP 模块 | 对应原模块 | 职责 |
|---|---|---|
| **api** | M01 + M03 + M04 + M22 | REST 入口、路由、参数校验、能力查询 |
| **session** | M05 + M06 | 会话生命周期（MVP 中 Session = Run） |
| **board** | M07 | board_profile 解析与加载 |
| **engine** | M09 + M10 | 离散事件调度、虚拟时间、步进控制 |
| **devices** | M14 | GPIO / UART / I2C 设备模型（插件式） |
| **diagnosis** | M15 + M16 + M17 + M18 + M21 | 事件处理 + 事实提取 + 解释生成（含规则） |
| **scenario** | M08 | YAML 场景加载、执行、断言 |
| **artifacts** | M19 + M20 | 状态查询 + 产物导出（事件日志、复现包） |

### 3.1 模块联动（简化主链路）

```
Agent/IDE
  |
  v
[api] -- REST 请求 --> [session] -- 创建/管理会话
                            |
                            v
                    [board] -- 加载硬件描述
                            |
                            v
                    [engine] -- 离散事件调度
                        |
                        v
                    [devices] -- GPIO/UART/I2C 模型
                        |
                        v
                    [diagnosis] -- 事件 -> 事实 -> 解释
                        |
                        v
                    [artifacts] -- 日志/复现包
                        |
                        v
                    [api] -- 返回响应给调用方
```

### 3.2 场景执行链路

```
[api] 加载场景请求
  |
  v
[scenario] 解析 YAML -> 生成动作时间线和断言
  |
  v
[engine] 按时间线推进，执行动作
  |
  v
[devices] 处理总线操作
  |
  v
[diagnosis] 生成诊断
  |
  v
[scenario] 执行断言，输出 PASS/FAIL
  |
  v
[artifacts] 导出结果
```

---

## 4. 数据模型（简化版）

### 4.1 Session（MVP 中 Session = 一次执行）

```python
class Session:
    session_id: str          # UUID
    board_profile: str       # 板级描述文件路径
    mode: str = "device_sim" # MVP 固定为 device_sim
    seed: int = 0            # 确定性种子
    created_at: datetime
    status: str              # "active" | "finished" | "error"
```

### 4.2 SimEvent（统一事件）

```python
class SimEvent:
    event_id: str
    session_id: str
    t_virtual_ns: int        # 虚拟时间（纳秒）
    source: str              # 例如 "device.i2c0"
    type: str                # 例如 "BUS_TIMEOUT"
    severity: str            # "info" | "warn" | "error"
    payload: dict
```

### 4.3 DiagnosticFact（诊断事实）

```python
class DiagnosticFact:
    fact_id: str
    session_id: str
    kind: str                # 例如 "bus_stuck_low"
    params: dict             # 例如 {"bus": "i2c0", "line": "sda", "duration_ms": 12.3}
    source_events: list[str] # 关联的 event_id 列表
```

### 4.4 Explanation（解释输出）

```python
class Explanation:
    hypothesis: str          # 候选原因
    confidence: float        # 0.0 ~ 1.0
    observations: list[str]  # 引用的 fact_id
    next_actions: list[str]  # 建议操作
    uncertainty_note: str | None  # 置信度低时填写
```

---

## 5. API 设计（最小集，6 个端点）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/v1/capabilities` | 返回支持的总线、设备类型（静态） |
| POST | `/v1/sessions` | 创建会话（传入 board_profile、seed） |
| POST | `/v1/sessions/{sid}/step` | 推进仿真时间 |
| POST | `/v1/sessions/{sid}/io/{bus}:{action}` | 总线操作（gpio:set, i2c:transact, uart:write） |
| GET | `/v1/sessions/{sid}/state` | 获取当前状态 + 事件 + 诊断 |
| POST | `/v1/sessions/{sid}/scenario:run` | 加载并执行场景，返回 PASS/FAIL + 解释 |

说明：
- 原 v2 中的 `start_run`、`finalize_run`、`events?since=`、`diagnostics`、`artifacts:export` 在 MVP 中合并到 `state` 和 `scenario:run` 的响应中。
- 减少端点数量 = 减少实现量 + 减少调用方学习成本。

---

## 6. 响应格式（保持原设计）

成功：
```json
{
  "ok": true,
  "request_id": "req-uuid",
  "data": { ... }
}
```

失败（带解释）：
```json
{
  "ok": false,
  "request_id": "req-uuid",
  "error": {
    "error_code": "I2C_BUS_STUCK_LOW",
    "message": "I2C transact timeout",
    "explain": "检测到 SDA 持续低电平，疑似上拉缺失或从设备占线。",
    "observations": ["SDA low for 12.3ms", "No rising edge after START"],
    "next_actions": ["检查上拉电阻配置", "隔离从设备逐个验证"]
  }
}
```

---

## 7. board_profile.yaml（保持原设计，略做精简）

```yaml
version: v1alpha1
board: my_stm32f4_dev
buses:
  i2c0:
    pins: { sda: PB7, scl: PB6 }
    pullup_ohm: 4700
    devices:
      - addr_7bit: 0x48
        type: TMP102
  uart0:
    pins: { tx: PA2, rx: PA3 }
    baud: 115200
gpio:
  PA0: { direction: output, pull: none }
  PA1: { direction: input, pull: up }
```

---

## 8. 场景 DSL（保持 v2 的三段结构）

```yaml
version: v1alpha1
setup:
  board_profile: ./profiles/stm32f4.yaml
  seed: 42

stimulus:
  - at_ms: 0
    action: gpio.set
    params: { pin: PA0, value: 1 }
  - at_ms: 5
    action: fault.inject
    params: { kind: i2c_sda_stuck_low, bus: i2c0, duration_ms: 20 }

assertions:
  - within_ms: 50
    expect_event:
      type: BUS_TIMEOUT
  - within_ms: 100
    expect_diagnosis:
      contains: "上拉"
```

---

## 9. 解释规则（MVP 内置，不需要 Registry）

MVP 阶段直接用 Python dict/函数实现规则，不需要独立的 Rulebook Registry 模块。

示例规则结构：

```python
RULES = [
    {
        "match": {"fact_kind": "bus_stuck_low", "bus_type": "i2c"},
        "hypothesis": "I2C SDA 线被拉低，可能原因：上拉电阻缺失或阻值过大、从设备异常占线",
        "confidence": 0.8,
        "next_actions": ["检查上拉电阻配置", "逐个隔离从设备排查"]
    },
    {
        "match": {"fact_kind": "repeated_nack", "bus_type": "i2c"},
        "hypothesis": "I2C 目标地址无应答，可能原因：地址配置错误、设备未上电、设备损坏",
        "confidence": 0.85,
        "next_actions": ["确认从设备 7-bit 地址", "检查设备供电", "用逻辑分析仪确认总线波形"]
    },
    {
        "match": {"fact_kind": "gpio_direction_conflict"},
        "hypothesis": "GPIO 引脚方向配置与操作不匹配",
        "confidence": 0.95,
        "next_actions": ["检查引脚初始化代码中的方向设置"]
    },
]
```

---

## 10. 建议目录结构

```
lot/
  main.py                  # FastAPI 入口
  api/
    routes.py              # 6 个 API 端点
    models.py              # Pydantic 请求/响应模型
  session/
    manager.py             # 会话管理
  board/
    loader.py              # board_profile 解析
  engine/
    clock.py               # 虚拟时间
    scheduler.py            # 离散事件队列
  devices/
    base.py                # 设备插件基类
    gpio.py
    uart.py
    i2c.py
  diagnosis/
    facts.py               # 事实提取
    rules.py               # 解释规则（内置）
    explainer.py            # 解释生成
  scenario/
    parser.py              # YAML 解析
    runner.py              # 场景执行与断言
  artifacts/
    store.py               # 事件日志与复现包导出
  profiles/                # board_profile 文件
    example_stm32f4.yaml
  scenarios/               # 场景文件
    example_i2c_stuck.yaml
  tests/
    test_api.py
    test_engine.py
    test_devices.py
    test_diagnosis.py
    test_scenario.py
```

---

## 11. 实施计划（面向大一新生调整）

### 阶段 1：骨架跑通（2~3 周）

- FastAPI 项目搭建 + 6 个 API 端点（可先返回 mock 数据）。
- Session 管理（创建/查询）。
- board_profile 加载。
- Pydantic 模型定义。

验收：能通过 HTTP 创建会话，返回正确 JSON。

### 阶段 2：仿真引擎 + GPIO（2~3 周）

- 虚拟时钟 + 离散事件队列。
- GPIO 设备模型（set/get/方向检查）。
- 第一条解释规则（GPIO 方向冲突）。

验收：通过 API 设置 GPIO，方向错误时返回带 explain 的错误响应。

### 阶段 3：UART + I2C + 诊断（3~4 周）

- UART 模型（波特率匹配 + 字节流）。
- I2C 模型（地址 + 读写事务 + NACK + 超时 + 上拉规则）。
- 诊断事实提取 + 解释规则扩充。

验收：I2C 上拉缺失场景能给出正确的 explain + observations。

### 阶段 4：场景回放 + 产物导出（2~3 周）

- YAML 场景解析与执行。
- 断言引擎（expect_event / expect_diagnosis）。
- 事件日志导出 + 最小复现包。

验收：一个完整场景 YAML 能跑通并输出 PASS/FAIL。

### 总计：约 9~13 周

---

## 12. 与原架构的关系

本文件是原架构在 MVP 阶段的**实施裁剪**，不是推翻。当 MVP 完成后，向原架构演进的路径是：

1. Session/Run 拆分 → 恢复 v2 的三层数据模型。
2. 加入 M02 MCP Facade → 支持 Claude Code/Cursor 等工具调用。
3. 加入 M11/M12 Renode Adapter → 支持 Mode B。
4. 事件处理模块拆分 → 恢复 M15/M16 的归一化/分级。
5. 规则外置 → 恢复 M21 Rulebook Registry。

原架构文档作为**长期目标参考**保留，本文件作为**当前执行指南**。
