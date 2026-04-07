# Diagnosis 模块架构报告

## 1. 模块定位

`diagnosis` 是项目的差异化核心。它把执行层产生的事件转为诊断事实，再把事实转为“证据绑定的解释、候选原因和下一步建议”。

MVP 映射关系：

- 对应长期模块 `M15 Event Normalizer`
- 对应长期模块 `M16 Event Classifier`
- 对应长期模块 `M17 Diagnostic Facts Engine`
- 对应长期模块 `M18 Explanation Engine`
- 对应长期模块 `M21 Rulebook Registry`

## 2. 核心职责

1. 消费统一事件流。
2. 提取诊断事实。
3. 用规则匹配生成候选原因。
4. 输出证据绑定的解释结果。
5. 给 `api` 和 `artifacts` 提供结构化诊断对象。

## 3. 诊断流水线

标准流水线：

`Raw Events -> Feature Extraction -> Diagnostic Facts -> Explanation Rules -> Hints`

## 4. 核心数据模型

```python
class DiagnosticFact:
    fact_id: str
    session_id: str
    kind: str
    params: dict
    source_events: list[str]
```

```python
class Explanation:
    hypothesis: str
    confidence: float
    observations: list[str]
    next_actions: list[str]
    uncertainty_note: str | None
```

## 5. 内部子结构建议

1. `normalizer`
2. `classifier`
3. `facts`
4. `rules`
5. `explainer`

## 6. 事实提取设计

典型事实：

1. `bus_stuck_low(bus=i2c0,line=sda,duration_ms=12.3)`
2. `repeated_nack(bus=i2c0,addr=0x48,count=3)`
3. `gpio_direction_conflict(pin=PA3,expected=out,actual=in)`
4. `uart_baud_mismatch(bus=uart0,expected=115200,observed=9600)`

## 7. 规则层设计

规则要求：

1. 必须给出证据引用。
2. 必须给出可执行下一步建议。
3. 置信度低时必须说明不确定性。

## 8. 与其他模块的协作

上游：

1. `engine`
2. `devices`

下游：

1. `api`
2. `scenario`
3. `artifacts`

## 9. 硬约束

1. `diagnosis` 只能基于统一事件或诊断事实工作，不能依赖设备私有内存结构。
2. 没有证据链时不得输出 hypothesis。
3. 规则层和解释层必须可替换，不能把所有逻辑耦合进一个函数。
4. `diagnosis` 不得调用 `api` 反向拿数据，所需数据必须由调用方传入。

## 10. 公开接口要求

```python
class DiagnosisService:
    def ingest_events(self, session_id: str, events: list[dict], board_profile: dict | None = None) -> dict: ...
    def get_latest_report(self, session_id: str) -> dict: ...
    def explain_error(self, session_id: str, error_code: str | None = None) -> dict | None: ...
```

接口要求：

1. `ingest_events` 返回值至少包含 `facts`、`explanations`。
2. `get_latest_report` 必须返回稳定结构，供 `api/scenario/artifacts` 共同消费。
3. `explain_error` 只能基于已有 report 提取结果。

## 11. 并行实现接缝

1. `diagnosis` 先冻结 `DiagnosticFact` 和 `Explanation` 结构。
2. `api/scenario/artifacts` 都只能读取这两个公开结构。
3. 规则表内部可演进，但外部结果结构不能随意变化。

## 12. MVP 范围

必须做：

1. 统一事件输入
2. 事实提取器
3. MVP 规则集合
4. 解释对象输出

暂不做：

1. 独立 Rulebook Registry 服务
2. LLM 自由生成解释
3. 复杂分层事件采样策略
4. 多后端专用解释分支

## 13. 演进路径

1. 从内置规则表升级到长期 `M21 Rulebook Registry`。
2. 把当前统一入口拆成 `M15/M16/M17/M18` 独立模块。
3. 为 LLM agent 提供结构化证据输入。

## 14. 验收标准

1. 无证据不输出 hypothesis。
2. 每条 explanation 都能追溯到 facts 或 events。
3. 常见 GPIO/UART/I2C 误配都能形成稳定解释。
