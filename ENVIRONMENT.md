# LOT 环境说明

## 1. 基线环境

- Python: `3.11+`
- 包管理: `pip`
- 虚拟环境: 推荐使用 `venv`
- 操作系统: Windows / Linux / macOS

当前 MVP 依赖的主要技术栈：

- FastAPI
- Pydantic v2
- PyYAML
- Uvicorn

说明：

- 当前仓库是可运行的 MVP 骨架，不是完整产品。
- 当前默认只支持 `Mode A / device_sim`。
- 当前主范围是 `GPIO / UART / I2C`。

## 2. 依赖文件

仓库当前的依赖声明文件：

- [requirements.txt](D:/projects2/Lot/requirements.txt)
- [pyproject.toml](D:/projects2/Lot/pyproject.toml)

如果只是本地运行，直接使用 `requirements.txt` 即可。

## 3. 创建虚拟环境

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

如果你希望像普通包一样直接 `import lot`，也可以执行：

```bash
pip install -e .
```

## 4. 启动方式

项目源码包位于：

- [src/lot](D:/projects2/Lot/src/lot)

FastAPI 入口位于：

- [main.py](D:/projects2/Lot/src/lot/main.py)

这个仓库采用 `src/` 布局，所以默认推荐从仓库根目录使用显式 `--app-dir src` 启动，而不是依赖当前 shell 已经设置好 `PYTHONPATH`。

### 推荐启动命令

#### Windows PowerShell / Linux / macOS 通用

```bash
python -m uvicorn --app-dir src lot.main:app --reload --host 0.0.0.0 --port 8000
```

### 如果已经执行过 `pip install -e .`

这时也可以直接运行：

```bash
uvicorn lot.main:app --reload --host 0.0.0.0 --port 8000
```

### 不推荐但可用的方式

如果你明确知道自己在做什么，也可以手动设置 `PYTHONPATH=src` 后再启动。但这不应作为默认文档入口，因为它更依赖 shell 环境状态。

启动后默认访问：

- `http://127.0.0.1:8000`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

## 5. 当前目录约定

核心源码目录：

- [api](D:/projects2/Lot/src/lot/api)
- [session](D:/projects2/Lot/src/lot/session)
- [board](D:/projects2/Lot/src/lot/board)
- [engine](D:/projects2/Lot/src/lot/engine)
- [devices](D:/projects2/Lot/src/lot/devices)
- [diagnosis](D:/projects2/Lot/src/lot/diagnosis)
- [scenario](D:/projects2/Lot/src/lot/scenario)
- [artifacts](D:/projects2/Lot/src/lot/artifacts)

输入样例目录：

- [profiles](D:/projects2/Lot/profiles)
- [scenarios](D:/projects2/Lot/scenarios)

架构文档目录：

- [report](D:/projects2/Lot/report)

## 6. 当前代码状态

当前代码状态可以概括为“可继续协作的 MVP 骨架”，特点如下：

- 模块边界已经固定
- 公共模型与跨模块协议已经固定
- API 主链路已经打通
- 核心能力已经可以跑通最小闭环
- 仍有一部分实现是面向后续扩展的 Stub 风格

后续开发应优先在模块内部补实现，不要轻易改动以下边界文件：

- [models.py](D:/projects2/Lot/src/lot/contracts/models.py)
- [protocols.py](D:/projects2/Lot/src/lot/contracts/protocols.py)
- [facade.py](D:/projects2/Lot/src/lot/api/facade.py)
- [bootstrap.py](D:/projects2/Lot/src/lot/bootstrap.py)

## 7. 已知限制

- 未安装依赖时，`import lot.main` 会因为缺少 `fastapi`、`pydantic` 等包而失败。
- 当前没有单独拆分开发依赖文件。
- 当前未接入数据库，运行产物仍然落在文件系统目录中。
- 当前未实现 `MCP / Renode / QEMU / WebSocket / SSE`。

## 8. 建议后续补充

如果后面要继续完善环境层，建议按这个顺序补：

1. 增加 `requirements-dev.txt`
2. 增加 `pytest` 或统一测试入口脚本
3. 增加 `.env.example`
4. 增加启动脚本，例如 `scripts/run.ps1` 和 `scripts/run.sh`
5. 增加 CI 基础检查
