# API 模块架构报告

## 1. 模块定位

`api` 是整个系统的统一接入层，负责把 Agent、IDE 或脚本请求转换成平台内部可执行的标准命令。它是 MVP 的第一入口，也是后续 MCP、JSON-RPC、REST 等多协议入口的收敛点。

MVP 映射关系：

- 对应长期模块 `M01 API Gateway`
- 对应长期模块 `M03 Command Router`
- 对应长期模块 `M04 Capability Service`
- 对应长期模块 `M22 Schema Registry`

## 2. 核心职责

1. 提供 REST API 单入口。
2. 统一请求解析、参数校验、错误封装和返回格式。
3. 提供能力发现接口 `capabilities`。
4. 把外部命令路由到 `session / scenario / engine / artifacts` 等内部模块。
5. 保证 `request_id`、`api_version`、错误码等契约稳定。

## 3. 不负责什么

1. 不执行设备仿真逻辑。
2. 不直接操作 GPIO/UART/I2C 语义。
3. 不直接生成诊断解释规则。
4. 不直接持久化工件内容。

## 4. 对外接口

MVP 最小端点：

1. `GET /v1/capabilities`
2. `POST /v1/sessions`
3. `POST /v1/sessions/{sid}/step`
4. `POST /v1/sessions/{sid}/io/{bus}:{action}`
5. `GET /v1/sessions/{sid}/state`
6. `POST /v1/sessions/{sid}/scenario:run`

统一响应格式：

```json
{
  "ok": true,
  "request_id": "req-uuid",
  "data": {}
}
```

统一错误格式：

```json
{
  "ok": false,
  "request_id": "req-uuid",
  "error": {
    "error_code": "I2C_BUS_STUCK_LOW",
    "message": "I2C transact timeout",
    "details": {},
    "explain": "检测到 SDA 持续低电平。",
    "observations": [],
    "next_actions": []
  }
}
```

## 5. 输入与输出

输入：

1. HTTP JSON 请求。
2. `board_profile` 路径或内容引用。
3. 场景 YAML 路径或文本。
4. Agent 的总线操作命令。

输出：

1. 结构化成功响应。
2. 稳定错误码和解释信息。
3. 会话状态、事件摘要、诊断结果、场景运行结果。

## 6. 内部子结构建议

1. `routes`
2. `models`
3. `dispatcher`
4. `capabilities_provider`
5. `error_mapper`

## 7. 关键数据契约

建议 API 内部命令对象：

```python
class ApiCommand:
    request_id: str
    session_id: str | None
    kind: str
    params: dict
```

建议能力对象：

```python
class Capabilities:
    modes: list[str]
    buses: list[str]
    device_types: list[str]
    scenario_version: str
    api_version: str
```

## 8. 核心工作流

创建会话：

1. 接收 `POST /v1/sessions`。
2. 校验 `board_profile`、`seed`、`mode`。
3. 调用 `session` 创建执行上下文。
4. 返回 `session_id` 和初始状态。

执行 I/O：

1. 接收总线事务命令。
2. 校验参数。
3. 调用 `engine` 驱动 `devices` 执行。
4. 从 `diagnosis` 获取最新解释。
5. 返回状态、事件和诊断。

## 9. 依赖关系

上游：

1. Agent
2. IDE
3. CLI

下游：

1. `session`
2. `board`
3. `engine`
4. `scenario`
5. `artifacts`

## 10. 硬约束

1. `api` 只能依赖其他模块的公开 service interface，不能直接读写别的模块内部状态。
2. `api` 不能自己拼装诊断解释文本，只能转发 `diagnosis` 产物。
3. `api` 不能保存业务真状态，任何 session 真实状态必须回到 `session/engine/artifacts`。
4. 路由层、模型层、错误映射层必须分离，不能把业务逻辑堆在 route handler。
5. 所有公开端点都必须接受和返回稳定 schema。

## 11. 公开接口要求

```python
class ApiFacade:
    def get_capabilities(self) -> dict: ...
    def create_session(self, payload: dict) -> dict: ...
    def step_session(self, session_id: str, payload: dict) -> dict: ...
    def execute_io(self, session_id: str, bus_action: str, payload: dict) -> dict: ...
    def get_state(self, session_id: str) -> dict: ...
    def run_scenario(self, session_id: str, payload: dict) -> dict: ...
```

接口要求：

1. 所有方法都返回可序列化字典或 Pydantic 模型。
2. 不向下游暴露 FastAPI `Request/Response` 对象。
3. `bus_action` 必须是稳定字符串，如 `gpio:set`、`i2c:transact`。

## 12. 并行实现接缝

1. `api` 先定义请求响应模型和 facade 协议，其他模块据此对接。
2. 如果下游未完成，允许使用 stub service，但字段名不得后改。
3. `api` 对下游的唯一假设是公开方法签名，不得依赖内部类名。

## 13. MVP 范围

必须做：

1. REST API
2. Pydantic 校验
3. 稳定错误码
4. `capabilities`
5. 6 个 MVP 端点

暂不做：

1. MCP facade
2. WebSocket / SSE
3. 运行时 schema registry 服务
4. 复杂鉴权限流

## 14. 演进路径

1. 把 dispatcher 分化成独立 `M01 + M03`。
2. 把能力发现抽成独立 `M04`。
3. 把 schema 版本管理抽成独立 `M22`。
4. 再额外挂接 `M02 MCP Tool Facade`。

## 15. 验收标准

1. 所有非法输入都能得到稳定错误码。
2. 所有成功响应都包含 `ok/request_id/data`。
3. API 层不写设备规则，不做解释推断。
