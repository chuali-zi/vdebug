本次补齐了 `scenario` 模块的核心 TODO：`parser` 现在会校验 YAML、兼容嵌套 DSL 与归一化 DSL，并输出排序后的 `ScenarioPlan`；`runner` 已可按时间线推进 `engine`、派发 `fault/gpio/uart/i2c` 动作、汇总 `diagnosis` 结果并执行 `expect_event / expect_diagnosis / expect_state` 断言；`service` 已在模块内组装默认依赖，外部契约未改。

注意事项：
1. `contracts.ScenarioResult` 目前没有 `events_summary/diagnosis_summary` 字段，且 `run_plan(runtime, plan)` 拿不到 `SessionRecord`，所以这里只能保持 `snapshot=None`，未跨模块改合同。
2. `scenarios/example_i2c_stuck.yaml` 当前只有一次普通 `i2c.transact`，没有 `fault.inject`，按现有 `diagnosis` 规则会返回 `fail`，这是样例/联动问题，不是 `scenario` runner 崩溃。
3. `engine` 当前公开事件名对 I2C 动作使用 `I2C_TRANSACT`，不是设备层的 `I2C_TRANSACTION`；本模块已按公开事件模型消费，未跨模块修正。
