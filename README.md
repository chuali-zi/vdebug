# LOT

**LOT**（本仓库包名 `lot`）是一个面向 **智能体（Agent）协作** 的 **嵌入式虚拟调试** 平台 **MVP 脚手架**：用 FastAPI 暴露版本化 HTTP API，在进程内组合「会话 / 板卡配置 / 虚拟时钟与调度 / 设备总线插件 / 诊断 / 场景 DSL / 运行产物」等模块边界，便于后续替换 Stub 实现或接入真实仿真与硬件。

当前定位为 **可运行的架构骨架**：核心流程已贯通，多数服务仍为 Stub，但引擎、板卡 YAML、设备插件与场景解析等已有可测行为。

## 功能概览

- **会话**：创建会话、按虚拟时间步进、查询状态；会话与运行时状态可持久化到 `runtime_sessions/`。
- **板卡配置**：从 YAML 加载 `BoardProfile`（含总线、GPIO 等），路径相对于进程工作目录解析。
- **设备仿真**：GPIO / UART / I2C 等设备以插件形式注册到 `DeviceRegistry`，引擎通过 `execute_io` 派发 `bus:action`。
- **诊断**：对步进与 IO 产生的事件做轻量分析，写入诊断事实与解释（Stub 可扩展规则）。
- **场景**：支持 `v1alpha1` 场景 DSL（YAML），可断言事件等；运行结束可导出 repro bundle 类产物。
- **产物**：事件流、快照、说明等写入 `runtime_artifacts/<session_id>/`（默认配置，见 `bootstrap`）。

## 环境要求

- Python **3.11+**
- 依赖见 `pyproject.toml` / `requirements.txt`（FastAPI、Pydantic v2、PyYAML、Uvicorn）

## 安装

在项目根目录：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -e .
```

或仅安装依赖：

```bash
pip install -r requirements.txt
```

安装 editable 包后，可直接 `import lot` 并运行 Uvicorn（推荐）。

## 启动 HTTP 服务

在**项目根目录**启动（便于板卡 YAML 与 `runtime_*` 目录解析一致）：

```bash
uvicorn lot.main:app --reload --host 0.0.0.0 --port 8000
```

- OpenAPI 文档：<http://127.0.0.1:8000/docs>
- 应用工厂：`lot.main:create_app`，路由前缀 **`/v1`**

## API 速览（`/v1`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/capabilities` | 模式、总线、设备类型等能力描述 |
| `POST` | `/sessions` | 创建会话（`board_profile`、`seed`、`mode`） |
| `POST` | `/sessions/{id}/step` | 虚拟时间前进 `delta_ms` |
| `POST` | `/sessions/{id}/io/{bus}:{action}` | 执行总线 IO |
| `GET` | `/sessions/{id}/state` | 当前状态视图 |
| `POST` | `/sessions/{id}/scenario:run` | 运行场景（`scenario_path` 与 `scenario_text` 二选一） |

成功响应为统一信封：`{ "ok": true, "request_id": "...", "data": { ... } }`；错误时为 `ok: false` 与结构化 `error`（含 `error_code`、`message` 等）。

## 仓库结构（`src/lot`）

| 目录 | 职责 |
|------|------|
| `api/` | FastAPI 路由、请求/响应模型、`ApiFacade` 编排 |
| `contracts/` | 跨模块领域模型、错误类型、Protocol 接口 |
| `session/` | 会话与运行时上下文 |
| `board/` | 板卡 YAML 解析与校验 |
| `engine/` | 虚拟时钟、调度队列、步进与 IO 执行 |
| `devices/` | 设备插件与注册表 |
| `diagnosis/` | 事实、规则、解释（Stub） |
| `scenario/` | 场景 DSL 解析与运行 |
| `artifacts/` | 运行中追加数据、状态视图、导出 bundle |
| `bootstrap.py` | `AppContainer` 装配与默认路径（`runtime_artifacts` 等） |

## 测试

测试通过 `sys.path` 指向 `src`，可直接在未 editable 安装时运行：

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

或单个模块：

```bash
python -m unittest tests.test_api -v
```

## 本地目录说明

- **`runtime_sessions/`**、**`runtime_artifacts/`**：默认运行时输出，已在 `.gitignore` 中忽略。
- **`report/`**：本地报告/笔记类目录，默认忽略；如需纳入版本管理可调整 `.gitignore`。

## 版本

包版本与 `pyproject.toml` 中一致（当前 **0.1.0**）。

---

本 README 描述的是仓库当前实现；随着 Stub 被替换为真实后端，部署方式、配置项与安全要求会相应变化。
