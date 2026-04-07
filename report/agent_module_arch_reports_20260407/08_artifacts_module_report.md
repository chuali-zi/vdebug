# Artifacts 模块架构报告

## 1. 模块定位

`artifacts` 是状态查询、日志沉淀和最小复现包导出模块。它负责把执行过程沉淀成可回看、可比较、可回归的产物。

MVP 映射关系：

- 对应长期模块 `M19 State Query Service`
- 对应长期模块 `M20 Artifact Service`

## 2. 核心职责

1. 提供当前状态查询。
2. 保存事件流、诊断结果和执行摘要。
3. 导出最小复现包。
4. 为后续 CI 和回归比较提供基础材料。

## 3. 不负责什么

1. 不直接执行设备动作。
2. 不解析场景 DSL。
3. 不生成解释规则。
4. 不作为系统调度入口。

## 4. 输入与输出

输入：

1. 来自 `engine` 的事件。
2. 来自 `diagnosis` 的事实和解释。
3. 来自 `session` 的元数据。
4. 来自 `board/scenario` 的配置来源。

输出：

1. 状态快照。
2. 事件日志。
3. 诊断日志。
4. 最小复现包路径或内容索引。

## 5. 推荐工件类型

1. `session_meta.json`
2. `event_stream.ndjson`
3. `diagnostic_facts.ndjson`
4. `explanations.json`
5. `state_snapshot.json`
6. `repro_bundle/`

## 6. 内部子结构建议

1. `state_query`
2. `event_store`
3. `diagnosis_store`
4. `bundle_exporter`

## 7. 状态查询设计

`GET /state` 建议聚合：

1. 当前会话状态
2. 当前虚拟时间
3. 近期事件摘要
4. 近期诊断结果
5. 关键设备状态快照

## 8. 持久化策略

MVP 推荐：

1. 以文件系统为主。
2. 事件流用 NDJSON，便于流式追加。
3. 摘要对象用 JSON，便于读取。
4. 每个会话单独目录，保证隔离。

## 9. 与其他模块协作

上游：

1. `session`
2. `engine`
3. `diagnosis`
4. `scenario`

下游：

1. `api`
2. 后续 `CI harness`

## 10. 硬约束

1. `artifacts` 不得成为业务真状态来源，真状态仍属于 `session/engine/diagnosis`。
2. `artifacts` 只能消费公开结构，不能读取其他模块私有运行时对象。
3. 所有落盘文件必须绑定 `session_id`，目录结构必须稳定。
4. 导出失败不能破坏主执行流程，只能返回附带错误。

## 11. 公开接口要求

```python
class ArtifactService:
    def record_events(self, session_id: str, events: list[dict]) -> None: ...
    def record_diagnosis(self, session_id: str, report: dict) -> None: ...
    def snapshot_state(self, session_id: str, state: dict) -> None: ...
    def get_state_view(self, session_id: str) -> dict: ...
    def export_repro_bundle(self, session_id: str) -> dict: ...
```

接口要求：

1. `get_state_view` 是 `api` 的唯一状态读取入口。
2. `export_repro_bundle` 返回至少包含 `bundle_path` 和 `included_files`。
3. 任何记录接口都只接受可序列化对象。

## 12. 并行实现接缝

1. `artifacts` 先冻结目录结构和文件名约定。
2. `engine/diagnosis/scenario` 只负责把公开对象交给这里，不负责决定落盘路径。
3. 后续 `CI harness` 直接基于本模块导出的结构工作。

## 13. MVP 范围

必须做：

1. 状态查询
2. 事件日志保存
3. 诊断结果保存
4. 最小复现包导出

暂不做：

1. 复杂索引检索服务
2. 数据库存储
3. 差异对比 UI
4. 长期冷热分层存储

## 14. 演进路径

1. 从 `session_id` 过渡到 `run_id` 绑定。
2. 为 `CI harness` 提供标准基线比对输入。
3. 拆出长期 `M19` 与 `M20`。

## 15. 验收标准

1. 每次执行都能导出最小复现包。
2. `state` 查询能稳定反映当前执行状态。
3. 事件和诊断日志可被机器再次消费。
