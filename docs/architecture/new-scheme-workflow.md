# 新增审查类型工作流 (New Scheme Workflow)

在 Hermes review control plane 的现行架构下，“新增一种新的审查方案（如挖掘工程、模板工程）”主**不再需要修改 Python 核心代码**。框架已经完全转化为配置驱动（Configuration as Source of Truth）。

## 主路径工作流 (Main Path)

当您需要为一个新的施工业务、审查对象种类或法务类型添加审查能力时，需遵循以下 4 步治理边界流程：

### 1. 新增法制/基线依据 (Knowledge files)
将新的规范原始文档或精简提取要求（Markdown 或 Text）放入 `knowledge/review_basis/` 相应的分类子目录下。
确保版本稳定，以作正式基线查询支持。

### 2. 注册依据至依据中心 (Basis Registry)
在 `config/review_basis/basis_registry.yaml` 中，为你新加的依据分配一个在全域唯一的 `basis_id`。
定义其 `source_type`，`effective_status`，并绑定对应的文件路径（`file_refs`）。

### 3. 创建/关联对应的审查包裹 (Packs & Rule Packs)
- **审查实体包 (Pack)**：在 `config/review_basis/pack_registry.yaml` 中定义一个新的 `pack`。把这套包与其所需要携带的 `basis_ids` 阵列绑定。
- **审查规则包 (Rule Pack)**：在 `config/review_basis/rule_pack_registry.yaml` 中为大语言模型定义所需的审查维度列表（如：一致性、合规性要求），并关联上方的 Pack。

### 4. 发布档案关联映射 (Profile Mapping)
在 `config/review_basis/profile_mapping.yaml` 中增加此类型的档案项。
例如：你的新方案类型是 `excavation_special_scheme`。
你需要定义：
```yaml
excavation_special_scheme:
  profile_id: "excavation_special_scheme"
  classification:
    level1: "BuildingConstruction"
    level2: "DangerousProjects"
  default_pack_ids:
    - "excavation.core.base"
  rule_pack_ids:
    - "excavation.core.v1"
```

---

## 退出机制与系统自动处理

通过上述 YAML 的配置完毕后：
1. **输入解析拦截**：当前端传入 `documentType: "excavation_special_scheme"`；
2. **ProfileResolver自动分发**：会检索到新增的 profile mapping；
3. **BasisPackResolver受限读取**：仅提取定义的包和 basis，绝不超量加载无关基准以污染上下文；
4. **Hermes** 接手进行原子级评审。

### 剩余可能需要写 Python 的技术债点？
目前对于基础审查而言：**无需写任何 Python 代码。**

**唯一的边界**：如果在上游解析器（如 Router）无法推断原始文件的泛读意图，不能精准返回 `excavation_special_scheme` 这种分类名词，则可能需要在 `apps/api/src/orchestrator/router.py` 中的 `infer_review_document_type()` 做几个关键字判断，但这属于前置 Router 轻处理，不再影响 Hermes 执行主链自身的隔离性。

未来甚至可以通过通用 LLM Router 一步转化。
