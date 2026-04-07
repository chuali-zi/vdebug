# LOT 环境要求与启动说明

## 1. 基线环境

- Python: `3.11+`
- 包管理: `pip`
- 虚拟环境: 推荐使用 `venv`
- 操作系统: Windows / Linux / macOS 均可

当前 MVP 骨架基于以下技术栈：

- FastAPI
- Pydantic v2
- PyYAML
- Uvicorn

说明：

- 当前仓库是“架构骨架 + 模块接缝”，不是完整业务实现。
- 现阶段默认只支持 `Mode A: device_sim`。
- 现阶段默认范围只覆盖 `GPIO / UART / I2C` 的模块预留，不包含具体协议细节实现。

## 2. 依赖文件

仓库当前有两份依赖声明：

- [requirements.txt](D:\projects2\Lot\requirements.txt)
- [pyproject.toml](D:\projects2\Lot\pyproject.toml)

建议优先使用 `requirements.txt` 快速安装运行依赖。

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

## 4. 启动方式

项目源码根包位于：

- [src/lot](D:\projects2\Lot\src\lot)

FastAPI 应用入口位于：

- [main.py](D:\projects2\Lot\src\lot\main.py)

推荐启动命令：

```powershell
$env:PYTHONPATH="src"
uvicorn lot.main:app --reload
```

如果是 Linux / macOS：

```bash
PYTHONPATH=src uvicorn lot.main:app --reload
```

启动后默认访问：

- `http://127.0.0.1:8000`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

## 5. 当前目录约定

核心源码目录：

- [api](D:\projects2\Lot\src\lot\api)
- [session](D:\projects2\Lot\src\lot\session)
- [board](D:\projects2\Lot\src\lot\board)
- [engine](D:\projects2\Lot\src\lot\engine)
- [devices](D:\projects2\Lot\src\lot\devices)
- [diagnosis](D:\projects2\Lot\src\lot\diagnosis)
- [scenario](D:\projects2\Lot\src\lot\scenario)
- [artifacts](D:\projects2\Lot\src\lot\artifacts)

输入样例目录：

- [profiles](D:\projects2\Lot\profiles)
- [scenarios](D:\projects2\Lot\scenarios)

架构文档目录：

- [report](D:\projects2\Lot\report)

## 6. 当前模块状态

目前代码状态是“可继续协作的骨架”，特点如下：

- 模块边界已经固定。
- 公共数据对象和跨模块协议已经固定。
- API 主链路已经接通。
- 核心业务实现大部分保留为 `TODO`。

后续 agent 应优先在各模块内部补实现，不要轻易改动以下边界文件：

- [models.py](D:\projects2\Lot\src\lot\contracts\models.py)
- [protocols.py](D:\projects2\Lot\src\lot\contracts\protocols.py)
- [facade.py](D:\projects2\Lot\src\lot\api\facade.py)
- [bootstrap.py](D:\projects2\Lot\src\lot\bootstrap.py)

## 7. 当前已知限制

- 尚未安装依赖时，`import lot.main` 会因缺少 `fastapi` 或 `pydantic` 失败。
- 当前仅做运行依赖声明，尚未单独拆分开发依赖。
- 当前未接入测试框架配置文件。
- 当前未接入数据库，产物目录仍是文件系统占位设计。
- 当前未实现 MCP / Renode / QEMU / WebSocket / SSE。

## 8. 建议后续补充

如果后面要继续完善环境层，建议按下面顺序追加：

1. 增加 `requirements-dev.txt`
2. 增加 `pytest` 与基础测试目录
3. 增加 `.env.example`
4. 增加 `Makefile` 或 PowerShell 启动脚本
5. 增加 CI 基础检查
