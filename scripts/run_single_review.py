import os
import sys
import json
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
apps_api = repo_root / 'apps' / 'api'
sys.path.insert(0, str(apps_api))

os.environ.setdefault('LLM_MODEL', 'qwen3.6-plus-2026-04-02')
config_path = os.getenv('LLM_CONFIG_PATH')
if config_path:
    try:
        with open(config_path) as f:
            cfg = json.load(f)
            if 'dashscope' not in cfg and 'aliyun' in cfg:
                os.environ.setdefault('LLM_CONFIG_PROFILE', 'aliyun')
    except Exception as e:
        print(f"Could not read configured LLM config: {e}")

from src.review.pipeline import StructuredReviewExecutor
from src.services.document_loader import DocumentLoader
from src.adapters.llm_gateway import LLMGateway
from src.config.llm import resolve_llm_config
from src.adapters.fastgpt_adapter import FastGPTAdapter

def main():
    config = resolve_llm_config()
    print(f"Using LLM config: {config.sanitized()}")
    
    llm = LLMGateway(config=config)
    executor = StructuredReviewExecutor(
        document_loader=DocumentLoader(),
        llm_gateway=llm,
        fast_adapter=None
    )
    
    files_to_review = [
        {
            "task_id": "review-peihua",
            "path": repo_root / "fixtures/supervision/施工组织设计-培花初期雨水调蓄池建设工程.pdf",
            "type": "construction_org",
            "out": repo_root / "fixtures/supervision/review-control-plane审查结果-施工组织设计培花初期雨水调蓄池建设工程.md"
        },
        {
            "task_id": "review-cold-rolling",
            "path": repo_root / "fixtures/supervision/施工组织设计-冷轧厂2030单元三台行车电气系统改造.docx",
            "type": "construction_org",
            "out": repo_root / "fixtures/supervision/review-control-plane审查结果-施工组织设计-冷轧厂2030单元三台行车电气系统改造.md"
        }
    ]
    
    for item in files_to_review:
        item["out"].parent.mkdir(parents=True, exist_ok=True)
        print(f"Running review for {item['path'].name}...")
        
        result = executor.run_sync(
            task_id=item["task_id"],
            query="对该文件执行正式结构化审查",
            source_document_path=str(item["path"]),
            document_type=item["type"],
            discipline_tags=[],
            strict_mode=True,
            policy_pack_ids=[]
        )
        
        report = result.get('reportMarkdown', '')
        if report:
            item["out"].write_text(report, encoding='utf-8')
            print(f"Saved report to {item['out']}")
        else:
            print(f"Failed to generate report for {item['path'].name}. Result keys: {result.keys() if isinstance(result, dict) else type(result)}")

if __name__ == '__main__':
    main()
