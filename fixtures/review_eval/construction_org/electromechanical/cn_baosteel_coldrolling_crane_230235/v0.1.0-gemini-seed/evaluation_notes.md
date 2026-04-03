# evaluation_notes

## purpose
- 用作机电安装类施工组织设计的 bootstrap seed case
- 验证目录结构异常、visibility gap、危大识别推断、应急预案错配等问题模式
- 用作后续 `structured_review` 的 parser / rule engine / report builder 回归样本

## primary_checks
- 是否能识别重复章节标题
- 是否能将附件引用与附件缺失区分开
- 是否能识别工期基准双重表述
- 是否能保留 Gemini seed 的危大工程、煤气区域、吊装承载力问题作为待复核项
- 是否能从原文抽出 22 台电机、7 天停机窗口、煤气区域等关键 facts

## known_limitations
- 当前 issue truth 不是专家确认结果
- 吊装专项方案缺失等问题暂不能自动视为 hard evidence
- 附件1/附件2 当前仅有引用关系，没有附件正文

## next_review_actions
- 补充附件可见性策略
- 结合 structured_review 规则核复核危大专项方案命中逻辑
- 人工复核煤气区域风险是否属于 L1 还是 L2
