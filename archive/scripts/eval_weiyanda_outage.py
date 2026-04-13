import os
import sys
import json
import asyncio
from pathlib import Path

repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))

# Set the LLM Config so it uses century.json
os.environ['LLM_MODEL'] = 'qwen3.6-plus'
os.environ['LLM_CONFIG_PATH'] = '/Users/lucas/control/secrets/api-keys/century.json'
try:
    with open(os.environ['LLM_CONFIG_PATH']) as f:
        cfg = json.load(f)
        if 'dashscope' not in cfg and 'aliyun' in cfg:
            os.environ['LLM_CONFIG_PROFILE'] = 'aliyun'
except Exception:
    pass

from src.main_dependencies import get_hermes_engine, get_document_loader
from src.review.contracts import ReviewBrief

async def main():
    print("Loading target document...")
    loader = get_document_loader()
    target_doc_path = repo_root / "fixtures/supervision/停电施工方案-威彦达.docx"
    doc_content = ""
    try:
        doc_content = loader.extract_text(target_doc_path)
    except Exception as e:
        print(f"Failed to load via document loader: {e}")
        sys.exit(1)
        
    print(f"Target document loaded, size: {len(doc_content)} chars")
    
    print("Loading standards...")
    standards = [
        "fixtures/construction/电网工程建设施工安全基准风险指南（2012年版）.md",
        "fixtures/construction/工程建设标准强制性条文 电力工程部分  2016年版.md",
        "fixtures/construction/中国南方电网公司电网建设工程专项施工方案管理工作指引（2022）.md",
        "fixtures/construction/中国南方电网基建施工方案全流程管控工作指引.md"
    ]
    policies_text = ""
    for std in standards:
        path = repo_root / std
        if path.exists():
            policies_text += f"\n--- {path.name} ---\n{path.read_text(encoding='utf-8')[:10000]}\n"
        else:
            print(f"Warning: std not found {path}")
            
    print("Constructing hermes review query...")
    engine = get_hermes_engine()
    
    query = (
        "请按以下五个维度对该《停电施工方案》进行严格的审查：\n"
        "1. 章节完整性\n"
        "2. 参数一致性\n"
        "3. 合法合规性\n"
        "4. 工序连贯性\n"
        "5. 证据验证\n\n"
        "以下是作为审查依据的4个规范标准内容片段，请仔细校对方案内容是否违背以下强制性要求：\n"
        f"{policies_text}\n"
    )
    
    brief = ReviewBrief(
        review_id="review-weiyanda-outage",
        review_object_type="construction_scheme",
        query=query
    )
    
    print("Monkey-patching httpx timeout to 300s to avoid LLM timeout on large contexts...")
    import httpx
    original_init = httpx.AsyncClient.__init__
    def patched_init(self, *args, **kwargs):
        kwargs['timeout'] = 300.0
        original_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = patched_init
    
    print("Executing hermes dual-path/router review...")
    # document_preview passed to the engine. The HermesRouterAdapter forwards this to the LLM adapter downstream.
    packet = await engine.review(brief=brief, document_preview=doc_content) 
    
    out_path = repo_root / "fixtures" / "supervision" / "停电施工方案-威彦达-hermes-review.md"
    
    # The FactPacket returned usually contains overall_assessment.
    report = packet.overall_assessment
    if not report and hasattr(packet, 'report_markdown') and packet.report_markdown:
        report = packet.report_markdown
        
    if not report:
        report = f"# 审查结果\n\n```json\n{packet.model_dump_json(indent=2)}\n```\n"

    out_path.write_text(report, encoding='utf-8')
    print(f"Review completed. Result saved to {out_path}")

if __name__ == '__main__':
    asyncio.run(main())
