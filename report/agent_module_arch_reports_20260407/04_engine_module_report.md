# Engine 模块架构报告

## 1. 模块定位

`engine` 是 MVP 的执行核心，负责虚拟时间、离散事件调度、步进控制和命令编排。它是 Mode A 的“强控制内核”。

MVP 映射关系：

- 对应长期模块 `M09 Control Core`
- 对应长期模块 `M10 Host-native Execution Engine`

## 2. 核心职责

1. 维护虚拟时钟。
2. 管理离散事件队列。
3. 执行 `step(ms)` 与按条件运行。
4. 调用 `devices` 完成总线语义操作。
5. 生成统一原始事件流，供 `diagnosis` 消费。

## 3. 不负责什么

1. 不对外暴露 HTTP 接口。
2. 不保存长期工件。
3. 不负责 YAML 场景解析。
4. 不直接输出最终解释文本。

## 4. 输入与输出

输入：

1. 来自 `api` 的步进或 I/O 命令。
2. 来自 `scenario` 的时间线动作。
3. 来自 `board` 的拓扑和设备配置。

输出：

1. 原始事件 `SimEvent`。
2. 状态快照。
3. 设备执行结果。

## 5. 核心数据模型

```python
class VirtualClock:
    now_ns: int
```

```python
class ScheduledEvent:
    due_ns: int
    priority: int
    seq: int
    kind: str
    payload: dict
```

```python
class SimEvent:
    event_id: str
    session_id: str
    t_virtual_ns: int
    source: str
    type: str
    severity: str
    payload: dict
```

## 6. 内部子结构建议

1. `clock`
2. `scheduler`
3. `executor`
4. `state_store`
5. `event_bus`

## 7. 调度规则

1. 同一时间戳下按 `priority` 排序。
2. 同一优先级按插入序排序。
3. 必须保证固定 `seed` 下的确定性。
4. 时间单位统一为 `ns`，对外可接收 `ms`。

## 8. 核心工作流

步进执行：

1. 接收 `step(ms)`。
2. 把目标时间换算成 `target_ns`。
3. 依次弹出 `due_ns <= target_ns` 的事件。
4. 调用对应设备或动作处理器。
5. 记录产生的 `SimEvent`。
6. 更新时间到目标值。

即时 I/O 执行：

1. 接收总线事务命令。
2. 交给 `devices` 对应驱动。
3. 接收事务结果和派生事件。
4. 将事件发送给 `diagnosis`。

## 9. 状态管理

最小状态集合：

1. 当前虚拟时间。
2. 待执行事件队列。
3. 各总线状态。
4. 各设备运行态。
5. 最近事件窗口。

## 10. 硬约束

1. `engine` 是虚拟时间与事件顺序的唯一裁决者，其他模块不得自增时间或私自改队列。
2. `engine` 只能通过 `devices` 公开接口驱动设备，不能直接改设备内部字段。
3. `engine` 输出事件必须使用统一 `SimEvent` 结构。
4. `engine` 不得依赖 HTTP、YAML 或文件系统细节。
5. `engine` 产生的平台内部错误必须与被测设备行为错误分开。

## 11. 公开接口要求

```python
class EngineService:
    def step(self, runtime: dict, delta_ms: int) -> dict: ...
    def execute_io(self, runtime: dict, bus_action: str, payload: dict) -> dict: ...
    def snapshot(self, runtime: dict) -> dict: ...
    def enqueue(self, runtime: dict, due_ns: int, kind: str, payload: dict, priority: int = 100) -> None: ...
```

接口要求：

1. `runtime` 由 `session` 提供。
2. `step` 返回值至少包含 `now_ns`、`events`、`state_delta`。
3. `execute_io` 返回值至少包含 `result`、`events`。
4. 任何事件都必须带 `session_id`。

## 12. 并行实现接缝

1. `engine` 先冻结 `SimEvent` 和 step result 结构。
2. `devices` 必须按这个结构返回派生事件。
3. `diagnosis` 只消费这个冻结后的统一事件，不消费 scheduler 内部对象。

## 13. MVP 范围

必须做：

1. 虚拟时钟
2. 离散事件队列
3. `step` 推进
4. GPIO/UART/I2C 操作调度
5. 统一事件输出

暂不做：

1. Mode B 编排
2. Renode/QEMU adapter hub
3. 分布式执行
4. 复杂实时调度模拟

## 14. 演进路径

1. 从 `engine` 中拆出长期的 `M09` 和 `M10`。
2. 为未来 `M11/M12/M13` 预留统一事件归一化入口。
3. 从单执行内核升级为“控制平面 + 可插拔后端”。

## 15. 验收标准

1. 同一 `scene + seed` 结果可复现。
2. `step` 能稳定推进并产生统一事件。
3. 设备动作不会绕开调度层。
