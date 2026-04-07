# Session 模块架构报告

## 1. 模块定位

`session` 是系统的执行上下文管理模块。在 MVP 中，`Session = 一次执行`，因此它同时承担长期架构中 `Session Service` 与 `Run Service` 的简化职责。

MVP 映射关系：

- 对应长期模块 `M05 Session Service`
- 对应长期模块 `M06 Run Service`

## 2. 核心职责

1. 创建、查询和关闭会话。
2. 维护会话级执行上下文。
3. 保存 `board_profile`、随机种子、模式和状态。
4. 为 `engine`、`scenario`、`artifacts` 提供统一会话句柄。
5. 维护最小资源隔离边界。

## 3. 不负责什么

1. 不解析板级 YAML 内容。
2. 不执行时间推进。
3. 不直接处理设备事务。
4. 不直接做解释推理。

## 4. 核心数据模型

```python
class Session:
    session_id: str
    board_profile: str
    mode: str
    seed: int
    created_at: datetime
    status: str
```

```python
class SessionRuntime:
    session_id: str
    board_topology: dict
    engine_state: dict
    device_registry: dict
    last_error: dict | None
```

## 5. 内部子结构建议

1. `manager`
2. `repository`
3. `runtime_registry`
4. `lifecycle`

## 6. 状态机

推荐状态：

1. `active`
2. `finished`
3. `error`

## 7. 核心工作流

创建会话：

1. 接收 API 请求参数。
2. 验证 `mode` 与 `seed`。
3. 调用 `board` 加载结构化硬件拓扑。
4. 初始化运行时上下文。
5. 返回 `session_id`。

查询会话状态：

1. 根据 `session_id` 读取元数据。
2. 拉取 `engine` 和 `artifacts` 的当前摘要。
3. 返回聚合状态。

## 8. 与其他模块的协作

上游：

1. `api`

下游：

1. `board`
2. `engine`
3. `scenario`
4. `artifacts`

## 9. 硬约束

1. `session` 是运行上下文唯一注册中心，其他模块不得自行创建平行上下文。
2. `session` 不得直接依赖 `diagnosis` 内部规则或 `devices` 私有对象实现细节。
3. `session` 存的运行态句柄必须是最小必要集合。
4. 会话状态迁移必须显式，不能通过隐式字段推断当前状态。

## 10. 公开接口要求

```python
class SessionService:
    def create(self, board_profile_ref: str, seed: int, mode: str = "device_sim") -> dict: ...
    def get(self, session_id: str) -> dict: ...
    def require_runtime(self, session_id: str) -> dict: ...
    def set_status(self, session_id: str, status: str) -> None: ...
    def close(self, session_id: str) -> None: ...
```

接口要求：

1. `require_runtime` 返回统一运行时容器，至少包含 `board_topology`、`engine_state`、`device_registry`。
2. `mode` 在 MVP 阶段只能接受 `device_sim`。
3. `session_id` 生成规则必须集中在本模块。

## 11. 并行实现接缝

1. `session` 要先把 runtime container 结构冻结，供 `engine/artifacts` 对接。
2. 其他模块只可读 runtime container 中约定字段，不可新增隐式字段。
3. 新字段只能由 `session` 模块 owner 扩展。

## 12. 持久化策略

MVP 建议：

1. 元数据以 JSON 存盘。
2. 运行态以内存为主。
3. 完成或异常时写一次最终快照。

## 13. MVP 范围

必须做：

1. 单层 Session 模型
2. 会话创建和查询
3. 运行态上下文保存
4. 状态迁移

暂不做：

1. 多 Run 管理
2. 权限域和租户隔离
3. 并发资源调度
4. 会话恢复和跨进程恢复

## 14. 演进路径

1. 拆出独立 `Run` 对象。
2. 把工件绑定从 `session_id` 升级到 `run_id`。
3. 把会话恢复、导出、列表能力补齐。

## 15. 验收标准

1. 每个会话都有唯一 `session_id`。
2. 会话状态变化可追踪。
3. 运行态上下文可被 `engine/scenario/artifacts` 复用。
