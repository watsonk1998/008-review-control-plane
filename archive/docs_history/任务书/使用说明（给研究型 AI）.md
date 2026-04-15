

使用说明（给研究型 AI）

1. 任务目标

请围绕 008-review-control-plane 当前仓库事实、本地 research pack 结构化证据、双样本监督材料与 V0.2 设计文档，产出以下治理文档之一或多份：
	•	《三角对比研究结果》（上游研究底稿，必须先于后三份完成）
	•	《V0.3 边界声明》
	•	《V0.2→V0.3 差距裁决与反过拟合约束清单》
	•	《双样本人工复核裁决稿（internal reviewed adjudication notes）》

你的目标不是输出"更像 Gemini 的报告"，也不是替系统做双样本提分，而是帮助项目形成更可信、可治理、可防过拟合的 structured_review 演进路线。

文档的依赖顺序与生产序列，请参阅本目录下的《V0.3 前置工作流程指南——文档生成顺序与依赖关系.md》。

2. 你必须承认的当前现实
	•	项目当前定位是 review control plane，不是成熟全栈 formal reviewer。
	•	structured_review 是正式结构化审查主链，review_assist 不等于正式审查结论。
	•	当前 official documentType 只包括：
	•	construction_org
	•	hazardous_special_scheme
	•	其他 documentType 即使已有 ready base pack，也不自动进入 official。
	•	PDF 当前仍是 pdf_text_only + parserLimited=True 的受限路径。
	•	本轮不引入 OCR / 多模态 / 图纸平台化 / 多文档批处理。
	•	Gemini 当前只能作为 seed / bootstrap substitute，不是 gold truth。
	•	当前没有完整人工裁决资源，因此任何 internal-reviewed 文档都不是 expert-golden。

3. 研究输入与证据层级

你的研究必须基于以下四层证据，并始终尊重它们的层级差异：

| 层级 | 来源 | 定位 | 注意事项 |
|------|------|------|----------|
| **第 1 层：GitHub 仓库事实** | README、docs/formal-review.md、fixtures/review_eval/README.md | **系统边界真相源** | 所有判断的顶层约束；边界声明不得与之冲突 |
| **第 2 层：本地 research pack** | `fixtures/research_inputs/` | **样本级结构化证据源** | 双样本 JSON / matrices / visibility / rule-hits 等结构化工件；是研究主输入，但属于运行产物，不等于长期版本化资产，不能替代 GitHub 仓库事实的系统边界真相源地位 |
| **第 3 层：Markdown 报告** | structured-review-report.md 等 | **人类可读呈现层** | 适合快速浏览和形成研究入口，但不应作为 truth 分层的主要依据；结构化 JSON 优先 |
| **第 4 层：Gemini** | Gemini deepresearch 结果 | **seed / candidate reference** | 仅可用于候选问题发现、差距探针、seed baseline、bootstrap substitute；不可用于最终真相仲裁、gold labels、规则答案库、prompt 风格模板 |

补充说明：
	•	`fixtures/research_inputs/` 下包含 manifest.json（完整工件清单）、双样本目录（各含 13 个结构化 JSON/matrix 文件）、eval/ 子目录（含 4 种评测 JSON）、latest-eval-summary.md（当前治理状态快照）
	•	latest-eval-summary.md 可作为阶段性辅助证据，但它不是长期仓库真相，更不能因为某次 eval 通过就自动认定差距已关闭
	•	研究型 AI 应优先消费结构化 JSON（如 structured-review-result.json、structured-review-l0-visibility.json、structured-review-rule-hits.json、各类 matrix），而非仅阅读 Markdown 报告

4. 你如何使用 Gemini

Gemini deepresearch 在本任务里只能用于：
	•	候选问题发现
	•	差距探针
	•	seed baseline
	•	bootstrap substitute

Gemini 不能用于：
	•	最终真相仲裁
	•	gold labels
	•	规则答案库
	•	prompt 风格模板
	•	"提到了就算成立、没提到就算不成立"的判断依据

5. 你如何处理双样本

双样本是高价值监督材料，但不是泛化证明。
你必须避免以下错误：
	•	围绕项目名写 patch
	•	围绕固定数字写特判
	•	围绕章节标题写模板逻辑
	•	围绕附件名写例外规则
	•	围绕 Gemini wording 做 style imitation

你必须优先把双样本中的问题抽象为通用机制缺口，例如：
	•	visibility taxonomy 不稳
	•	attachment state 区分不足
	•	fact taxonomy 不全
	•	clause applicability / evidence gap 闭环不足
	•	reviewer gate / promotion governance 不完整

处理双样本时，优先从 research pack 中的结构化 JSON 和 matrices 入手，而非仅从 Markdown 报告文案做归纳。

6. 你最应优先关注的能力层

本轮优先级不是平均铺开，而是明确聚焦：
	•	L0：visibility / parser / blocked-state / manual-review 可信度
	•	L2：fact → rule hit → clause applicability → evidence gap 闭环

L3 可以分析、可以保留、可以进 experimental / diagnostics，但不是本轮主攻目标。

7. 你必须采用的治理视角

你的所有判断都必须显式区分：
	•	official
	•	experimental
	•	diagnostics
	•	internal-reviewed
	•	seed
	•	gold

同时必须区分：
	•	issue truth
	•	visibility truth
	•	evidence truth
	•	enhancement only

不要把这些层级混在一起写。

8. 你如何处理证据不足

如果当前证据不够硬，你必须敢于写：
	•	暂不裁决
	•	待补证
	•	blocked_by_visibility
	•	enhancement only
	•	seed reference only

不要为了"像专家"而强行下硬结论。

9. 你的工作输出应服务什么

你的输出应服务于：
	•	收紧 V0.3 范围
	•	建立差距裁决闸门
	•	形成 internal-reviewed 准备层
	•	保护系统不被双样本过拟合带偏

而不是服务于：
	•	扩更多 documentType
	•	追 Gemini 文风
	•	直接生成宏大平台蓝图
	•	把 seed 当 gold

10. 你最不能做错的事

最不能做错的是：

把系统优化成"冷轧厂 + 培花 + Gemini 表达方式"的专用答题器。

与其让两份样本表现更像 Gemini，不如让系统在更多样本上更可信、更诚实地表达 visibility / applicability / evidence gap / manual review。

11. 你交付时必须自查

请在交付前确认：
	•	你没有偷偷扩 official scope
	•	你没有把 Gemini 当 gold
	•	你没有按样本词做建议
	•	你没有把 visibility truth 混成 issue truth
	•	你没有把 enhancement 混成 hard defect
	•	你输出的是治理文档，不是愿景文档
	•	你的 truth 分层判断优先依据了 research pack 中的结构化工件，而非仅凭 Markdown 报告文案
