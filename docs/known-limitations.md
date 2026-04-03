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

6. **structured_review 目前只支持最小单文件输入**
   - 当前支持 `fixtureId` 或单文件 `sourceDocumentRef` 上传。
   - 仍不支持多文档批处理、外部对象存储或多模态 OCR 平台化链路。

7. **P0 正式支持范围仍有限**
   - 当前正式支持仅 `construction_org` 与 `hazardous_special_scheme`。
   - `construction_scheme`、`supervision_plan`、`review_support_material` 仍保留 registry / skeleton 覆盖，但不计入 P0 成功标准。

8. **PDF 仍是 text-only 降级路径**
   - PDF 当前会显式输出 `pdf_text_extraction_only`、`pdf_tables_not_preserved`、`pdf_attachment_visibility_may_be_unknown` 等 warnings。
   - 因此 PDF 场景下的表格、图示与附件边界仍可能落入 `unknown` / `attachment_unparsed`，需要结合原件人工复核。

9. **strictMode 仍是保留字段**
   - 请求、持久化和结果中仍保留 `strictMode`，但当前不作为真实规则裁决开关。
   - UI 与文档已将其降级为 `reserved / no-op`，避免过度承诺。
