# Bug Changelog

## 2026-04-08

- 修复 `engine` 在 I/O 请求失败时先写入公开 runtime 状态的问题；现在只有设备层执行成功后才会提交 `gpio`、`uart`、`i2c` 聚合视图，避免失败请求污染状态。
- 修复 `artifacts` 导出的 `bundle.included_files` 被错误序列化为 JSON 字符串的问题；现在返回结构化列表。
- 修复 [README.md](D:/projects2/Lot/README.md) 末尾损坏的 NUL 残留内容，恢复为正常文本文件，避免被工具识别为二进制。
