# 测试记录

## 测试基线

### 后端单元/集成测试

命令：

```bash
cd /Users/lucas/repos/review/008-review-control-plane/apps/api
. .venv/bin/activate
pytest -q
```

当前结果：`7 passed`

### 前端构建检查

命令：

```bash
cd /Users/lucas/repos/review/008-review-control-plane/apps/web
npm run lint
npm run build
```

已通过。

## 功能测试矩阵

### 测试 1：标准问答

目标链路：DeepResearchRuntime → FastGPT → DeepTutor

已验证：

- 真实成功任务：`2e6e5025afe94556af23b20197a86a8e`
- 能看到 plan / events / Fast chunk / DeepTutor 返回

对应工件：

- `artifacts/tasks/2e6e5025afe94556af23b20197a86a8e/fast-dataset.json`
- `artifacts/tasks/2e6e5025afe94556af23b20197a86a8e/deeptutor.json`

### 测试 2：深度研究

目标链路：DeepResearchRuntime → GPT Researcher

验证方式：

- 通过 `scripts/verify_connectivity.sh` 保存联通工件
- 通过 API `taskType=deep_research` 或 adapter 直调验证报告生成

### 测试 3：文档研究

目标链路：fixture/docx → GPT Researcher

样本：

- `fixtures/copied/supervision/230235-冷轧厂2030单元三台行车电气系统改造-施工组织设计.docx`
- `fixtures/copied/supervision/监理实施规划（南校区宿舍楼）20250710(1).docx`

验证方式：

- adapter 直调
- API `taskType=document_research`

### 测试 4：审查辅助

目标链路：DeepResearchRuntime → FastGPT → DeepTutor / GPT Researcher → LLM

验收点：

- 输出“辅助审查要点”
- 明确“非正式审查结论”
- 有 sources / steps / artifacts

## 推荐回归命令

```bash
make test
make smoke
make verify-connectivity
```
