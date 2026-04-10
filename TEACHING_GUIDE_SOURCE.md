# LOT 源码实现导读

这份文档比 `TEACHING_GUIDE_BEGINNER.md` 更偏源码导读。

目标不是逐行讲每个函数，而是让你知道：

- 代码为什么要这样分层
- 请求进来后是怎么走的
- 这些模块之间是如何协作的

如果你把这份文档看懂，再去读 `src/`，会轻松很多。

## 1. 先看最外层：应用是怎么被组装出来的

源码入口在：

- [main.py](D:/projects2/Lot/src/lot/main.py)

这里做的事很少，核心是：

1. 调 `build_container()`
2. 创建 FastAPI app
3. 安装错误处理器
4. 注册路由

这个设计很重要，因为它说明：

- `main.py` 不直接实现业务
- 它只负责“把系统装起来”

这叫“装配层”思路。

## 2. `bootstrap.py` 是整个系统的装配中心

重点文件：

- [bootstrap.py](D:/projects2/Lot/src/lot/bootstrap.py)

它负责创建：

- `board_service`
- `session_service`
- `engine_service`
- `diagnosis_service`
- `scenario_service`
- `artifacts_service`
- `api_facade`

你可以把它理解成“把电脑主机组装好”的那个人。

为什么要有它？

因为如果每个模块到处自己创建别的模块，代码会很乱。

有了 `bootstrap` 之后：

- 谁依赖谁，一眼能看到
- 替换实现更容易
- 测试也更方便

## 3. API 层为什么不是直接写业务

重点文件：

- [routes.py](D:/projects2/Lot/src/lot/api/routes.py)
- [facade.py](D:/projects2/Lot/src/lot/api/facade.py)
- [models.py](D:/projects2/Lot/src/lot/api/models.py)
- [error_mapper.py](D:/projects2/Lot/src/lot/api/error_mapper.py)

这里体现了一个很标准的后端分层：

### 3.1 `routes.py`

负责：

- 定义 HTTP 路径
- 接收请求
- 调用 facade

它是“路由入口”。

### 3.2 `models.py`

负责：

- 定义请求模型
- 定义响应模型
- 做参数校验

它是“接口契约”。

### 3.3 `facade.py`

负责：

- 把多个模块串起来
- 组织一次 API 请求对应的业务流程

它是“编排层”。

### 3.4 `error_mapper.py`

负责：

- 把 Python 异常映射成 HTTP 错误响应
- 保持统一错误格式

它是“接口异常翻译器”。

所以 API 层不是在“做所有事情”，而是在：

- 接请求
- 编排流程
- 回响应

## 4. Session 为什么重要

重点文件：

- [service.py](D:/projects2/Lot/src/lot/session/service.py)
- [models.py](D:/projects2/Lot/src/lot/session/models.py)

### 4.1 `SessionRecord`

这是“这次运行的身份信息”，比如：

- session_id
- board_profile
- mode
- seed
- status

### 4.2 `RuntimeContext`

这是“这次运行真正的内部状态容器”。

里面包含：

- board 配置
- 虚拟时钟状态
- scheduler 队列
- device state
- 最近的事件、事实、解释

为什么要分成 `SessionRecord` 和 `RuntimeContext`？

因为：

- `SessionRecord` 更像元数据
- `RuntimeContext` 更像实时运行状态

一个偏“身份卡”，一个偏“工作台”。

## 5. Board 模块为什么单独存在

重点文件：

- [service.py](D:/projects2/Lot/src/lot/board/service.py)

Board 模块的职责不是执行，而是：

- 读取 YAML
- 做结构化校验
- 生成 `BoardProfile`

为什么不直接在 API 里读 YAML？

因为板卡配置本身就是一个独立领域。

它有自己的规则，比如：

- I2C 引脚是否合法
- UART baud 是否有效
- 引脚有没有重复占用

如果把这些逻辑塞到 API 或 engine，会让边界变脏。

## 6. Engine 是控制中心，不是设备本身

重点文件：

- [service.py](D:/projects2/Lot/src/lot/engine/service.py)
- [clock.py](D:/projects2/Lot/src/lot/engine/clock.py)
- [scheduler.py](D:/projects2/Lot/src/lot/engine/scheduler.py)

这里有三个关键角色：

### 6.1 `VirtualClock`

负责虚拟时间。

也就是：

- 当前时间是多少
- step 后前进多少
- 时间不能倒退

### 6.2 `SchedulerQueue`

负责未来事件队列。

它解决的是：

- 某个动作不是立刻执行，而是在未来某个时刻执行
- 哪个事件先执行，要按时间和优先级来排

### 6.3 `EngineService`

负责把这些东西真正串起来：

- 推进时间
- 取出到期事件
- 派发 I/O
- 生成统一事件

Engine 像“交通指挥中心”，而不是“司机本人”。

## 7. Devices 模块为什么是插件式

重点文件：

- [registry.py](D:/projects2/Lot/src/lot/devices/registry.py)
- [base.py](D:/projects2/Lot/src/lot/devices/base.py)
- [gpio.py](D:/projects2/Lot/src/lot/devices/gpio.py)
- [uart.py](D:/projects2/Lot/src/lot/devices/uart.py)
- [i2c.py](D:/projects2/Lot/src/lot/devices/i2c.py)

这里的核心思想是：

> 不同总线行为不一样，但对外接口要统一。

所以代码做法是：

1. 用 `DevicePlugin` 定义统一基类
2. 每种设备实现自己的 `handle()` / `inject_fault()`
3. 用 `DeviceRegistry` 统一注册
4. 用 `DeviceRuntime` 负责运行时调用

这样设计的好处是：

- 新增一种 bus 或设备时，不需要重写整个系统
- 只需要再加一个插件

这就是“开闭原则”的一个很朴素的工程体现：

- 对扩展开放
- 对大范围乱改关闭

## 8. Diagnosis 为什么要拆成 facts / rules / explainer

重点文件：

- [facts.py](D:/projects2/Lot/src/lot/diagnosis/facts.py)
- [rules.py](D:/projects2/Lot/src/lot/diagnosis/rules.py)
- [explainer.py](D:/projects2/Lot/src/lot/diagnosis/explainer.py)
- [service.py](D:/projects2/Lot/src/lot/diagnosis/service.py)

设计意图是避免“直接从事件跳结论”。

### 8.1 `facts.py`

负责把事件抽象成诊断事实。

例如：

- `I2C_BUS_STUCK_LOW` -> `bus_stuck_low`

### 8.2 `rules.py`

负责保存内置解释规则。

例如：

- 如果 fact 是 `repeated_nack`
- 那 hypothesis 可以怎么写
- confidence 大概是多少
- next_actions 给什么

### 8.3 `explainer.py`

负责真正生成解释文本。

### 8.4 `service.py`

负责把整个链路串起来。

所以 diagnosis 的真实结构是：

```text
events -> facts -> rules -> explanations
```

这是一种很典型的“证据链”思维。

## 9. Scenario 模块为什么像“小型脚本引擎”

重点文件：

- [parser.py](D:/projects2/Lot/src/lot/scenario/parser.py)
- [runner.py](D:/projects2/Lot/src/lot/scenario/runner.py)
- [service.py](D:/projects2/Lot/src/lot/scenario/service.py)

Scenario 模块做了两件事：

### 9.1 解析

把 YAML 变成结构化 `ScenarioPlan`

### 9.2 执行

按照时间顺序：

- 执行动作
- 推进时间
- 收集结果
- 执行断言

这和传统“读配置文件”不同，它更像“执行一个小脚本”。

所以如果你感觉 scenario 有点像测试框架，那是对的。

它本来就有一点这个味道。

## 10. Artifacts 模块为什么不可缺

重点文件：

- [service.py](D:/projects2/Lot/src/lot/artifacts/service.py)
- [store.py](D:/projects2/Lot/src/lot/artifacts/store.py)

很多初学者会忽略这一层，觉得“能返回结果就行”。

但在调试系统里，证据和复盘能力非常重要。

Artifacts 模块负责：

- 把事件追加进 `ndjson`
- 保存状态快照
- 保存 explanation
- 导出 repro bundle

这样你才能：

- 复盘问题
- 保存证据
- 给别人复现

这也是为什么它不是“可有可无”的边角料，而是主链路的一部分。

## 11. 统一模型为什么放在 `contracts`

重点文件：

- [models.py](D:/projects2/Lot/src/lot/contracts/models.py)
- [protocols.py](D:/projects2/Lot/src/lot/contracts/protocols.py)
- [errors.py](D:/projects2/Lot/src/lot/contracts/errors.py)

这是整个仓库里很“架构”的一层。

### 11.1 `models.py`

放公共数据模型，例如：

- `SessionRecord`
- `BoardProfile`
- `SimEvent`
- `DiagnosticFact`
- `Explanation`

### 11.2 `protocols.py`

放跨模块接口约定。

比如：

- Session service 至少要提供哪些方法
- Engine service 至少要提供哪些方法

### 11.3 `errors.py`

放统一领域错误类型。

这保证不同模块报错时还能被 API 层稳定处理。

所以 `contracts` 的作用是：

> 让整个系统讲同一种“数据语言”和“接口语言”。

## 12. 一次 API 请求到底怎么走

下面用 `POST /v1/sessions/{id}/scenario:run` 举例。

### 第一步

请求先进入：

- `api/routes.py`

它把请求体解析成模型对象。

### 第二步

路由调用：

- `ApiFacade.run_scenario(...)`

### 第三步

facade 会拿到：

- 当前 session
- 当前 runtime
- scenario payload

然后调用：

- `scenario_service.load_plan(...)`
- `scenario_service.run_plan(...)`

### 第四步

scenario runner 在执行过程中会继续调用：

- `engine.step(...)`
- `engine.execute_io(...)`

### 第五步

engine 再调用：

- devices runtime / plugins

### 第六步

执行产生 event 之后，会调用：

- `diagnosis.analyze(...)`

### 第七步

诊断和事件又会被送到：

- `artifacts.append_runtime_data(...)`

### 第八步

最后 API facade 再调用：

- `artifacts.export_bundle(...)`

### 第九步

最终结果作为统一 JSON 返回给请求方。

所以你要记住：

这个仓库不是“一个大函数算完所有事”，而是“多个模块逐层协作”。

## 13. 测试在源码层面是怎么验证的

### 13.1 API 测试验证什么

- 路由能不能调用
- 请求校验是否正确
- 错误结构是否统一

### 13.2 Engine 测试验证什么

- 时间推进是否正确
- 调度顺序是否正确
- 非法输入是否被拒绝
- 失败请求是否不会污染状态

### 13.3 Devices 测试验证什么

- GPIO / UART / I2C 的基本行为
- 故障注入是否生效

### 13.4 Scenario 测试验证什么

- plan 解析
- 断言执行
- bundle 导出

也就是说，测试不是在“证明作者心情很好”，而是在锁定系统行为。

## 14. 你读源码时的推荐顺序

不要从最细的地方开始啃。推荐按这个顺序读：

1. [main.py](D:/projects2/Lot/src/lot/main.py)
2. [bootstrap.py](D:/projects2/Lot/src/lot/bootstrap.py)
3. [api/facade.py](D:/projects2/Lot/src/lot/api/facade.py)
4. [contracts/models.py](D:/projects2/Lot/src/lot/contracts/models.py)
5. [session/models.py](D:/projects2/Lot/src/lot/session/models.py)
6. [engine/service.py](D:/projects2/Lot/src/lot/engine/service.py)
7. [devices/registry.py](D:/projects2/Lot/src/lot/devices/registry.py)
8. [diagnosis/service.py](D:/projects2/Lot/src/lot/diagnosis/service.py)
9. [scenario/runner.py](D:/projects2/Lot/src/lot/scenario/runner.py)
10. [artifacts/service.py](D:/projects2/Lot/src/lot/artifacts/service.py)

这个顺序的意义是：

- 先看全局
- 再看主链路
- 最后看细节

## 15. 你现在应该从哪开始练

如果你是第一次做这种项目，我建议你先做下面三种练习：

### 练习 1

自己画一张图，把下面这条链写出来：

```text
HTTP 请求 -> route -> facade -> service -> runtime -> event -> diagnosis -> artifact
```

### 练习 2

自己手写一遍：

- `POST /v1/sessions`
- `POST /v1/sessions/{id}/step`
- `GET /v1/sessions/{id}/state`

不用马上改源码，先口头解释每一步干了什么。

### 练习 3

随便选一个测试，比如：

- [test_engine.py](D:/projects2/Lot/tests/test_engine.py)

把它拆成：

1. 输入是什么
2. 调用了谁
3. 预期是什么
4. 为什么这样能说明功能正确

如果你能把这三种练习做明白，这个仓库你就已经不是“完全乱了”，而是进入了“能读懂并开始学工程”的阶段。
