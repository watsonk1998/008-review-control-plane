# 存储归档区 (Archive)

> [!WARNING]
> **面向开发者的告警**
> - 绝对禁止将此目录内的任何代码重新引入到目前的生产环境 (`src/`)！
> - 若有复用需求，必须全新实现。
> - 不要在这里维护旧代码的类型兼容，本文件夹不接受重构、样式美化、静态类型修正。

This directory contains historically deprecated code, outdated scripts, unlinked tests, and obsolete experimentation artifacts.
They are kept here to ensure a clean active tree while retaining history for manual review and confirmation before final deletion.

**目录指引**:
- `scripts/`: 已废弃验证脚本和评测任务的收容所（例如 `eval_full_task.py`）。
- `experimental/`: 失败或被抛弃的神农工程探针。

**清理策略**: 定期（如每季度）应安全清除掉 6. 个月以上未被借阅引用的文件。
