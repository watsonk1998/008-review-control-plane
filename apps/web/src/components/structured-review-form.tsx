import type { CreateTaskRequest, ReviewDocumentType, SupportScopeResponse } from "@/types/control-plane";
import { useState } from "react";

export interface StructuredReviewFormProps {
  form: CreateTaskRequest;
  setForm: React.Dispatch<React.SetStateAction<CreateTaskRequest>>;
  supportScope?: SupportScopeResponse | null;
}

const TAXONOMY = [
  {
    l1Key: "construction_org",
    l1Label: "施工组织设计类",
    families: [
      {
        l2Label: "施工组织总设计",
        documentType: "construction_org",
        tags: ["施工组织设计（含优化）"]
      },
      {
        l2Label: "单位工程组织设计",
        documentType: "construction_org",
        tags: ["专业及单位工程施工组织设计"]
      }
    ]
  },
  {
    l1Key: "hazardous_special_scheme",
    l1Label: "危大工程专项方案类",
    families: [
      {
        l2Label: "基坑工程",
        documentType: "hazardous_special_scheme",
        tags: ["[深]基坑支护与降水工程", "基坑土方开挖工程", "边坡防护与支护工程"]
      },
      {
        l2Label: "模板支撑体系",
        documentType: "hazardous_special_scheme",
        tags: ["[高大]模板支撑系统工程", "特殊结构模板工程（爬模/滑模/飞模）", "承重支撑架工程"]
      },
      {
        l2Label: "起重吊装与安拆",
        documentType: "hazardous_special_scheme",
        tags: ["塔式起重机安装与拆卸工程", "桥门式起重机安拆工程", "起重吊装作业工程（含群组/多机抬吊）"]
      },
      {
        l2Label: "脚手架工程",
        documentType: "hazardous_special_scheme",
        tags: ["落地式脚手架工程", "悬挑式脚手架工程", "附着式升降脚手架（爬架）工程", "各类卸料平台工程", "独立操作架/满堂架工程"]
      },
      {
        l2Label: "拆除工程",
        documentType: "hazardous_special_scheme",
        tags: ["建（构）筑物拆除工程", "大型设备或临时设施拆除工程"]
      },
      {
        l2Label: "暗挖工程",
        documentType: "hazardous_special_scheme",
        tags: ["隧道与暗挖开挖工程", "隧道初支与二衬工程", "工程爆破及静态爆破工程"]
      },
      {
        l2Label: "建筑幕墙安装工程",
        documentType: "hazardous_special_scheme",
        tags: ["各类建筑幕墙安装工程"]
      },
      {
        l2Label: "钢结构安装工程",
        documentType: "hazardous_special_scheme",
        tags: ["钢结构安装工程（含空间网架/索膜）"]
      },
      {
        l2Label: "配电配网工程",
        documentType: "distribution_network_special_scheme",
        tags: ["停电/涉电施工作业工程", "组塔架线专项工程"]
      },
      {
        l2Label: "顶管及水下工程",
        documentType: "hazardous_special_scheme",
        tags: ["非开挖顶管/拉管工程", "水下作业及围堰工程"]
      }
    ]
  },
  {
    l1Key: "construction_scheme",
    l1Label: "一般专项与管理体系类",
    families: [
      {
        l2Label: "场地与公用临设",
        documentType: "construction_scheme",
        tags: ["施工临时用电工程", "施工临时用水及总平布置", "绿色施工与扬尘治理"]
      },
      {
        l2Label: "地基与基础分部",
        documentType: "construction_scheme",
        tags: ["各类桩基施工工程", "地基处理工程", "防水排渗与土方回填"]
      },
      {
        l2Label: "主体结构分部",
        documentType: "construction_scheme",
        tags: ["混凝土结构工程（含预应力）", "砌体与装配式隔墙工程", "钢筋专项工程"]
      },
      {
        l2Label: "屋面与装饰装修",
        documentType: "construction_scheme",
        tags: ["屋面与地下防水/防渗工程", "综合装饰装修与抹灰工程"]
      },
      {
        l2Label: "机电、安装与管线",
        documentType: "construction_scheme",
        tags: ["给排水及管线迁改工程", "建筑电气与消防施工安装", "通风空调及特种设备（机房/电梯）"]
      },
      {
        l2Label: "路桥隧市政基建",
        documentType: "construction_scheme",
        tags: ["桥梁下部及上部结构工程", "道路施工及交通疏解保畅", "大型土石方运输及路面结构"]
      },
      {
        l2Label: "检测测量与质量",
        documentType: "construction_scheme",
        tags: ["工程测量与形变监测方案", "超前地质预报及监控量测", "首件工程及质量通病防治方案"]
      }
    ]
  },
  {
    l1Key: "supervision_plan",
    l1Label: "安全防范与应急管理类",
    families: [
      {
        l2Label: "灾害及应急预案",
        documentType: "construction_scheme",
        tags: ["自然灾害防范预案（防洪/防台等）", "安全事故应急预案（坍塌/中毒/火灾等）"]
      },
      {
        l2Label: "专项作业及风控",
        documentType: "construction_scheme",
        tags: ["有限空间施工作业方案", "危化品管控及动火作业专项", "重大危险源辨识与双控防范体系"]
      }
    ]
  }
];

export function StructuredReviewForm({ form, setForm }: StructuredReviewFormProps) {
  const [l1Key, setL1Key] = useState<string>(TAXONOMY[0].l1Key);
  const [l2Label, setL2Label] = useState<string>(TAXONOMY[0].families[0].l2Label);

  if (form.taskType !== "structured_review") {
    return null;
  }

  const selectedTags = new Set(form.disciplineTags || []);

  const handleL1Change = (newL1Key: string) => {
    const l1 = TAXONOMY.find(t => t.l1Key === newL1Key) || TAXONOMY[0];
    const defaultL2 = l1.families[0];
    setL1Key(newL1Key);
    setL2Label(defaultL2.l2Label);
    
    setForm(curr => ({
      ...curr,
      documentType: defaultL2.documentType as ReviewDocumentType,
      disciplineTags: []
    }));
  };

  const handleL2Change = (newL2Label: string) => {
    const l1 = TAXONOMY.find(t => t.l1Key === l1Key) || TAXONOMY[0];
    const l2 = l1.families.find(f => f.l2Label === newL2Label) || l1.families[0];
    setL2Label(newL2Label);
    
    setForm(curr => ({
      ...curr,
      documentType: l2.documentType as ReviewDocumentType,
      disciplineTags: []
    }));
  };

  const toggleTag = (tag: string, checked: boolean) => {
    setForm(curr => {
      const set = new Set(curr.disciplineTags || []);
      if (checked) set.add(tag);
      else set.delete(tag);
      return { ...curr, disciplineTags: Array.from(set) };
    });
  };

  const currentL1 = TAXONOMY.find(t => t.l1Key === l1Key) || TAXONOMY[0];
  const currentL2 = currentL1.families.find(f => f.l2Label === l2Label) || currentL1.families[0];

  return (
    <div className="stack-lg">
       <div className="form-grid review-profile-grid">
        <label className="field">
          <span style={{ fontWeight: 600, color: "#334155" }}>【单选】业务领域与一级分类</span>
          <select
            value={l1Key}
            onChange={(e) => handleL1Change(e.target.value)}
            style={{ padding: "10px", borderColor: "#CBD5E1", borderRadius: "6px" }}
          >
            {TAXONOMY.map(l1 => (
              <option key={l1.l1Key} value={l1.l1Key}>{l1.l1Label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="field">
        <div className="stack-md">
           <div className="stack-sm">
             <strong style={{ display: "block", marginBottom: "8px", color: "#475569" }}>【单选】方案大类</strong>
             <div className="review-discipline-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                {currentL1.families.map((family) => (
                   <label className="checkbox-row inline-check" key={family.l2Label} style={{ background: "#F1F5F9", padding: "12px", borderRadius: "6px", border: l2Label === family.l2Label ? "1px solid #0B192C" : "1px solid transparent", cursor: "pointer" }}>
                     <input
                       type="radio"
                       name="l2_family"
                       checked={l2Label === family.l2Label}
                       onChange={() => handleL2Change(family.l2Label)}
                     />
                     <span style={{ fontWeight: l2Label === family.l2Label ? 600 : 400, color: "#0F172A" }}>
                       {family.l2Label}
                     </span>
                   </label>
                ))}
             </div>
           </div>

           {currentL2.tags.length > 0 && (
               <div className="stack-sm" style={{ marginTop: "16px" }}>
                 <strong style={{ display: "block", marginBottom: "8px", color: "#475569" }}>【多选】附加细分专项（按需叠加）</strong>
                 <div className="review-discipline-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    {currentL2.tags.map((tag) => (
                       <label className="checkbox-row inline-check" key={tag} style={{ background: selectedTags.has(tag) ? "#F0F9FF" : "#F8FAFC", padding: "10px", borderRadius: "6px", border: selectedTags.has(tag) ? "1px solid #7DD3FC" : "1px solid #E2E8F0", cursor: "pointer" }}>
                         <input
                           type="checkbox"
                           checked={selectedTags.has(tag)}
                           onChange={(e) => toggleTag(tag, e.target.checked)}
                         />
                         <span style={{ color: "#334155" }}>{tag}</span>
                       </label>
                    ))}
                 </div>
               </div>
           )}
        </div>
      </div>
    </div>
  );
}
