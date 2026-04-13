import sys

with open('/Users/lucas/knowledge/domains/personal/time/01-日记系统/2026/2026-04/2026-04-13.md', 'r') as f:
    content = f.read()

new_log = """
- **Hermes 审查参数穹顶突破 (Qwen3.6-Plus 支持)**：
  - **解封 Input/Output Token 瓶颈：** 基于实际模型能力评估，清除了所有旧架构中遗留的抠门字符串截断与强制设限。将子 Agent（事实抽取）和表达层 Agent 输入拉升至 `200k Token`，主核 Hermes Agent 的输入推高至 `500k Token`；全系 Agent `max_tokens` 统一锁定至极高水位的 `20000`。
  - **消除阶段性断头失败：** 彻底杜绝由于内部大数组 JSON （十余个发现点） 超编引发的生成中断导致的 `fallback` 截面积失真，用真正的机器管线去匹配长篇超大基建方案审查。
"""

# Insert before "## 🤖 机器摘要层"
target = "## 🤖 机器摘要层"
content = content.replace(target, new_log.strip() + "\n\n" + target)

with open('/Users/lucas/knowledge/domains/personal/time/01-日记系统/2026/2026-04/2026-04-13.md', 'w') as f:
    f.write(content)
