# Scenario 模块架构报告

## 1. 模块定位

`scenario` 是场景驱动与回归闭环模块。它把 YAML DSL 转成可执行时间线，并在执行完成后给出断言结果。

MVP 映射关系：

- 对应长期模块 `M08 Scenario Service`

## 2. 核心职责

1. 解析场景 DSL。
2. 构建 `setup/stimulus/assertions` 三段执行计划。
3. 驱动 `engine` 和 `devices` 执行动作。
4. 执行事件、状态、诊断断言。
5. 返回 PASS/FAIL 与证据。

## 3. 不负责什么

1. 不保存长期工件。
2. 不维护外部 API。
3. 不自己实现设备语义。
4. 不绕过 `engine` 直接修改运行态。

## 4. 输入与输出

输入：

1. 场景 YAML。
2. `session_id`。
3. 可选 `seed`、`board_profile` 覆盖项。

输出：

1. 结构化 `ScenarioPlan`。
2. 运行结果 `PASS/FAIL`。
3. 失败断言对应证据。

## 5. DSL 结构

MVP 推荐固定三段：

1. `setup`
2. `stimulus`
3. `assertions`

## 6. 内部子结构建议

1. `parser`
2. `planner`
3. `runner`
4. `assertions`
5. `reporter`

## 7. 核心工作流

1. 解析场景 DSL。
2. 校验 `version/setup/stimulus/assertions`。
3. 将刺激动作按时间排序。
4. 驱动 `engine` 推进时间并执行动作。
5. 从 `diagnosis/artifacts` 获取事件和解释。
6. 对断言做匹配。
7. 输出 PASS/FAIL 和失败证据。

## 8. 断言类型建议

MVP 支持：

1. `expect_event`
2. `expect_diagnosis`
3. `expect_state`

## 9. 与其他模块协作

上游：

1. `api`

下游：

1. `engine`
2. `devices`
3. `diagnosis`
4. `artifacts`

## 10. 硬约束

1. `scenario` 只能通过 `engine` 和公开 service interface 驱动执行，不能直改 runtime 内部状态。
2. `scenario` 不得重复实现设备语义或诊断规则。
3. 断言必须消费公开事件、状态或诊断结构，不能读取私有对象。
4. 场景 DSL 的语义必须稳定，不能因实现方便随意改字段名。

## 11. 公开接口要求

```python
class ScenarioService:
    def parse(self, payload: str | dict) -> dict: ...
    def plan(self, parsed: dict) -> dict: ...
    def run(self, session_id: str, scenario_plan: dict) -> dict: ...
```

接口要求：

1. `run` 返回值至少包含 `passed`、`assertions`、`events_summary`、`diagnosis_summary`。
2. `plan` 输出必须是排序后的标准时间线。
3. `parse` 错误必须定位到字段或步骤。

## 12. 并行实现接缝

1. `scenario` 先冻结 DSL schema 和 `ScenarioResult` 结构。
2. `api` 只负责转发输入输出，不持有 DSL 细节。
3. `artifacts` 可直接消费 `ScenarioResult`，无需理解 runner 内部过程。

## 13. MVP 范围

必须做：

1. YAML DSL 解析
2. 时间线动作调度
3. 事件类和诊断类断言
4. PASS/FAIL 汇总

暂不做：

1. 复杂分支脚本语言
2. 多场景并发编排
3. 远程依赖下载
4. DSL 插件生态

## 14. 演进路径

1. 从单次 `scenario:run` 扩展为长期 `Scenario Service`。
2. 增加 `setup` 中的固件和后端字段，支持 Mode B。
3. 让 CI harness 直接消费 `ScenarioPlan`。

## 15. 验收标准

1. 场景可稳定解析并执行。
2. 同一场景可复现同一断言结果。
3. 失败断言能附带证据链。
