# Devices 模块架构报告

## 1. 模块定位

`devices` 是系统的设备语义层，负责 GPIO、UART、I2C 等总线及其设备模型。它为平台提供“像硬件一样响应”的协议级行为，但不追求指令级或电路级全精度。

MVP 映射关系：

- 对应长期模块 `M14 Device Model Runtime`

## 2. 核心职责

1. 实现 GPIO/UART/I2C 的标准语义。
2. 按 `board` 配置实例化总线和设备。
3. 处理读写事务、状态变化和故障注入。
4. 向 `engine` 返回设备结果和原始事件。

## 3. 不负责什么

1. 不掌控全局时间。
2. 不生成最终解释文本。
3. 不暴露外部 API。
4. 不维护场景断言逻辑。

## 4. 输入与输出

输入：

1. `board` 输出的拓扑对象。
2. `engine` 发来的总线事务命令。
3. `scenario` 注入的故障动作。

输出：

1. 事务结果。
2. 设备状态变化。
3. 原始事件。

## 5. 插件抽象建议

```python
class DevicePlugin:
    name: str
    bus_type: str

    def init(self, config: dict) -> None: ...
    def handle(self, action: str, params: dict, now_ns: int) -> dict: ...
    def snapshot(self) -> dict: ...
```

## 6. 子架构拆分

GPIO：

1. 引脚方向管理。
2. 上拉/下拉状态。
3. `set/get` 与方向冲突检查。

UART：

1. 字节流收发。
2. 波特率配置校验。
3. 基础 framing / mismatch 表征。

I2C：

1. 地址寻址。
2. 读写事务。
3. NACK、超时、SDA/SCL 异常表征。
4. 上拉相关规则输入。

## 7. 与其他模块的协作

上游：

1. `engine`
2. `scenario`

下游：

1. `diagnosis`

协作约束：

1. `devices` 只输出事件和状态，不输出“原因解释”。
2. `devices` 不直接依赖 `api`。
3. `devices` 不直接依赖 `artifacts`。

## 8. 硬约束

1. `devices` 只能表达设备语义和状态变化，不能输出最终解释文案。
2. `devices` 不得直接读写工件存储、场景 DSL 或 HTTP 请求对象。
3. 所有总线行为都必须通过统一插件接口暴露，不能在 `engine` 里硬编码设备细节。
4. 设备插件产生的事件必须可转换为统一 `SimEvent`。

## 9. 公开接口要求

```python
class DeviceRuntime:
    def register_from_board(self, board_profile: dict) -> None: ...
    def execute(self, action: str, payload: dict, now_ns: int) -> dict: ...
    def inject_fault(self, fault_kind: str, payload: dict, now_ns: int) -> dict: ...
    def snapshot(self) -> dict: ...
```

接口要求：

1. `execute` 返回值至少包含 `result`、`events`。
2. `events` 中每一项都必须可转换为统一事件对象。
3. `snapshot` 返回值必须不含不可序列化对象。

## 10. 并行实现接缝

1. `devices` 先冻结 plugin base class 和 `execute` 返回结构。
2. `engine` 只依赖该结构，不依赖具体 GPIO/UART/I2C 类名。
3. `diagnosis` 只能依赖事件，不依赖设备实例字段。

## 11. 故障注入设计

MVP 推荐支持：

1. `i2c_sda_stuck_low`
2. `repeated_nack`
3. `gpio_direction_conflict`
4. `uart_baud_mismatch`

## 12. MVP 范围

必须做：

1. GPIO 基础模型
2. UART 基础模型
3. I2C 基础模型
4. 统一插件基类
5. 状态快照接口

暂不做：

1. SPI/ADC 大量设备族
2. 寄存器级精确模型
3. SPICE 电气级仿真
4. 大规模第三方插件生态

## 13. 演进路径

1. 扩充 SPI/ADC。
2. 把统一运行时升级为长期 `Device Model Runtime`。
3. 加入更丰富的 built-in 设备库。

## 14. 验收标准

1. 相同输入总线动作得到可复现输出。
2. GPIO/UART/I2C 都能输出统一事件。
3. 故障注入能稳定触发诊断链。
