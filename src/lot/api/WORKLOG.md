# API 工作日志

已完成：6 个 MVP 端点、统一 `ok/request_id/data|error` 响应、`request_id` 中间件、DomainError/校验错误/500 映射。已加 `tests/test_api.py` 覆盖成功与失败契约。后续查 bug 优先看 `routes.py`、`error_mapper.py`、`models.py`；若接口异常，先确认下游 stub 是否抛出稳定 `error_code`。
