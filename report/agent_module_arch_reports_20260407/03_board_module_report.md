# Board 模块架构报告

## 1. 模块定位

`board` 负责把 `board_profile.yaml` 转换成平台可执行的结构化硬件拓扑。它为 `engine`、`devices`、`diagnosis` 提供共同的板级事实来源。

MVP 映射关系：

- 对应长期模块 `M07 Board Profile Service`

## 2. 核心职责

1. 解析 `board_profile.yaml`。
2. 校验总线、引脚、设备和约束是否合法。
3. 输出结构化板级拓扑。
4. 为设备实例化和诊断规则提供硬件事实。

## 3. 不负责什么

1. 不执行场景。
2. 不维护会话生命周期。
3. 不推进虚拟时间。
4. 不直接输出诊断解释。

## 4. 输入与输出

输入：

1. 板级 YAML 文件路径。
2. 板级 YAML 原始文本。

输出：

1. `BoardProfile` 结构化对象。
2. 校验错误列表。
3. 设备实例化所需的标准拓扑信息。

## 5. 核心数据模型

```python
class BoardProfile:
    version: str
    board: str
    buses: dict
    gpio: dict
    power: dict | None
    constraints: dict | None
```

## 6. 内部子结构建议

1. `loader`
2. `schema`
3. `validator`
4. `normalizer`

## 7. 关键校验规则

1. `version` 必填。
2. 总线名字必须唯一。
3. 一个引脚不能在同一语义层被重复占用。
4. I2C 设备地址必须满足 7-bit 合法范围。
5. UART 默认波特率必须为正整数。

## 8. 核心工作流

1. 读取 YAML。
2. 用 Pydantic 解析。
3. 运行跨字段校验。
4. 归一化为内部标准对象。
5. 返回给 `session` 保存。

## 9. 硬约束

1. `board` 是板级配置的唯一解释来源，其他模块不得自行重复解析原始 YAML。
2. `board` 输出对象必须是归一化后的稳定结构。
3. `board` 不得为设备层补业务默认行为，只负责结构和约束。

## 10. 公开接口要求

```python
class BoardService:
    def load(self, board_profile_ref: str) -> dict: ...
    def validate(self, raw_payload: dict) -> list[dict]: ...
    def normalize(self, raw_payload: dict) -> dict: ...
```

接口要求：

1. `load` 返回的对象至少包含 `board`、`buses`、`gpio`。
2. `validate` 返回结构化错误列表，不直接抛裸字符串。
3. 下游只消费 `normalize/load` 的结果，不消费原始 YAML 字典。

## 11. 并行实现接缝

1. `board` 模块先冻结 `BoardProfile` 结构。
2. `devices` 和 `diagnosis` 只能依赖冻结后的结构字段。
3. 新字段只能追加，不能重命名已有语义字段。

## 12. MVP 范围

必须做：

1. GPIO/UART/I2C 三类结构化解析。
2. 基础字段校验与默认值处理。
3. 供 `devices/diagnosis` 消费的标准拓扑对象。

暂不做：

1. SPI/ADC 大量扩展字段。
2. 动态热插拔设备。
3. 复杂板级电源树建模。
4. 独立 board registry 服务。

## 13. 演进路径

1. 加入 `electrical`、`power`、`constraints` 更丰富模型。
2. 加入设备模型引用与版本管理。
3. 与长期 `Schema Registry` 联动。

## 14. 验收标准

1. 合法 YAML 能稳定转成标准对象。
2. 非法字段能给出明确错误。
3. `devices` 可只依赖 `BoardProfile` 完成实例化。
