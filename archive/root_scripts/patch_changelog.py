import sys

with open('CHANGELOG.md', 'r') as f:
    content = f.read()

new_log = """
- 全局解封大模型上下文限制阀值 (Context Window Limits)：基于 Qwen3.6-Plus 的实际运转能力验证，将底座架构中的输入字符天花板与输出 Token 锁死强行突破原生短板约束。其中：008子Agent 与表达分类 Agent 截断提升至 `200k Input / 20k Output`，Hermes主控 Agent 参数跃升至 `500k Input / 20k Output`。这一硬核调整彻底解决了大型分部工程长篇文书审核时，尾部规程被截断以及“由于 JSON 生成长度腰斩产生的严重遗漏”的系统级痛点报告干瘪问题。"""

# Find the spot after the latest entry
target = "### Changed\n"
content = content.replace(target, target + new_log.strip() + "\n")

with open('CHANGELOG.md', 'w') as f:
    f.write(content)
