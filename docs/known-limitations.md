# 已知限制

1. **DeepTutor 目前是 bridge 形态**
   - 008 复用了其真实 ChatAgent，但没有把官方完整 RAG/KB 栈全部启动。
   - 因此它更适合作为“知识问答/解释型能力服务”，而非完整 DeepTutor 平台镜像。

2. **GPT Researcher 依赖较重**
   - 已经通过 direct import + env bridge 打通。
   - 但完整 web/local research 调用延迟可能较高，首次运行会明显慢于普通问答。
   - 为了提升稳定性，008 对 `sourceUrls + useWeb=false` 增加了 static-source fallback；但若用户要求纯 web research，仍受外部搜索和抓取质量影响。

3. **FastGPT Mode B 依赖 collectionId**
   - 若没有明确 collectionId，只能优先走 Mode A。
   - Mode B 解析严格要求返回正文可 `JSON.parse`，否则 008 会显式保留 raw 并报错。

4. **当前前端优先使用 SSE，断流时回退轮询**
   - 详情页已经接入 `/api/tasks/{taskId}/stream`。
   - 当实时流中断时，前端会自动降级到 polling，而不是完全失去可观察性。

5. **审查辅助不是正式审查结论**
   - 当前输出是 control plane 级别的辅助整合结果，不能直接替代正式签发审查意见。

6. **structured_review 当前仍是 fixture-first**
   - P0 先把既有 formal review 骨架做稳，不在本阶段扩成通用上传、多文档批处理或多模态 OCR 平台。

7. **P0 正式支持范围仍有限**
   - 当前正式支持仅 `construction_org` 与 `hazardous_special_scheme`。
   - `construction_scheme`、`supervision_plan`、`review_support_material` 仍保留 registry / skeleton 覆盖，但不计入 P0 成功标准。
