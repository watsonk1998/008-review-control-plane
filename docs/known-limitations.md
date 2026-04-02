# 已知限制

1. **DeepTutor 目前是 bridge 形态**
   - 008 复用了其真实 ChatAgent，但没有把官方完整 RAG/KB 栈全部启动。
   - 因此它更适合作为“知识问答/解释型能力服务”，而非完整 DeepTutor 平台镜像。

2. **GPT Researcher 依赖较重**
   - 已经通过 direct import + env bridge 打通。
   - 但完整 web/local research 调用延迟可能较高，首次运行会明显慢于普通问答。

3. **FastGPT Mode B 依赖 collectionId**
   - 若没有明确 collectionId，只能优先走 Mode A。
   - Mode B 解析严格要求返回正文可 `JSON.parse`，否则 008 会显式保留 raw 并报错。

4. **当前前端使用轮询而非 SSE**
   - 这是为稳定性和实现成本做的取舍。

5. **审查辅助不是正式审查结论**
   - 当前输出是 control plane 级别的辅助整合结果，不能直接替代正式签发审查意见。
