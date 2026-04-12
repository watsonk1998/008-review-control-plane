import os
import sys
import json
import asyncio
from pathlib import Path

repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
sys.path.insert(0, str(repo_root / 'apps' / 'api'))

os.environ['LLM_MODEL'] = 'qwen3.6-plus'
os.environ['LLM_CONFIG_PATH'] = '/Users/lucas/tools/from-obsidian/AI/config/century.json'
try:
    with open(os.environ['LLM_CONFIG_PATH']) as f:
        cfg = json.load(f)
        if 'dashscope' not in cfg and 'aliyun' in cfg:
            os.environ['LLM_CONFIG_PROFILE'] = 'aliyun'
except Exception:
    pass

import httpx
original_init = httpx.AsyncClient.__init__
def patched_init(self, *args, **kwargs):
    kwargs['timeout'] = 300.0
    original_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = patched_init

from src.main_dependencies import get_task_service
from src.domain.models import CreateTaskRequest

async def main():
    service = get_task_service()
    
    target_doc_path = repo_root / "fixtures/supervision/停电施工方案-威彦达.docx"
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
            policies_text += f"\n--- {path.name} ---\n{path.read_text(encoding='utf-8')[:8000]}\n"
            
    query = (
        "请按以下五个维度对该《停电施工方案》进行严格的审查：\n"
        "1. 章节完整性\n"
        "2. 参数一致性\n"
        "3. 合法合规性\n"
        "4. 工序连贯性\n"
        "5. 证据验证\n\n"
        "以下是作为审查依据的4个规范标准内容片段，请仔细校对方案内容是否违背以下要求：\n"
        f"{policies_text}\n"
    )
    
    from src.domain.models import SourceDocumentRef
    req = CreateTaskRequest(
        taskType='structured_review',
        query=query,
        documentType='construction_scheme',
        sourceDocumentRef=SourceDocumentRef(
            refId='doc_weiyanda_1',
            sourceType='upload',
            fileName=target_doc_path.name,
            fileType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            storagePath=str(target_doc_path),
            displayName=target_doc_path.name,
        )
    )
    
    task = service.create_task(req)
    print(f"Created task: {task.id}")
    
    basis_files = []
    for std in standards:
        path = repo_root / std
        if path.exists():
            basis_files.append({'path': str(path), 'type': path.suffix.lstrip('.'), 'name': path.name})
            
    service.store.update_task(task.id, plan={
        'hermesInput': {
            'basis_files': basis_files,
            'focus_parts': [
                '章节完整性',
                '参数一致性',
                '合法合规性',
                '工序连贯性',
                '证据验证'
            ],
            'strict_mapping': True
        }
    })
    
    # Run synchronously to wait for result
    await service.runtime.execute_task(task.id)
    print("Task execution completed.")
    
    # Refresh task
    task = service.get_task(task.id)
    if not task or not task.result:
        print("No result found in task!")
        sys.exit(1)
        
    report = task.result.get('finalReportMarkdown') or task.result.get('reportMarkdown', '')
    if not report:
        print("No markdown report generated!")
        report = json.dumps(task.result, indent=2, ensure_ascii=False)
        
    out_path = repo_root / "fixtures/supervision/停电施工方案-威彦达-审查结果.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding='utf-8')
    print(f"Report saved to {out_path}")

    json_out_path = repo_root / "fixtures/supervision/停电施工方案-威彦达-审查结果.json"
    json_out_path.write_text(json.dumps(task.result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"JSON Report saved to {json_out_path}")

if __name__ == '__main__':
    asyncio.run(main())
