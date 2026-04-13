import os
import sys
import json
import asyncio
from pathlib import Path

repo_root = Path('/Users/lucas/repos/review/008-review-control-plane')
apps_api = repo_root / 'apps' / 'api'
sys.path.insert(0, str(apps_api))

os.environ['LLM_MODEL'] = 'qwen3.6-plus'
os.environ['LLM_CONFIG_PATH'] = '/Users/lucas/control/secrets/api-keys/century.json'
try:
    with open(os.environ['LLM_CONFIG_PATH']) as f:
        cfg = json.load(f)
        if 'dashscope' not in cfg and 'aliyun' in cfg:
            os.environ['LLM_CONFIG_PROFILE'] = 'aliyun'
except Exception:
    pass

from src.main_dependencies import get_hermes_controller
from src.review.contracts import ReviewBrief

async def main():
    print("Monkey-patching httpx timeout to 300s...")
    import httpx
    original_init = httpx.AsyncClient.__init__
    def patched_init(self, *args, **kwargs):
        kwargs['timeout'] = 300.0
        original_init(self, *args, **kwargs)
    httpx.AsyncClient.__init__ = patched_init

    print("Initializing Hermes Controller...")
    controller = get_hermes_controller()
    doc_path = str(repo_root / "fixtures/supervision/停电施工方案-威彦达.docx")
    
    print(f"Triggering execute() on {doc_path}...")
    brief = ReviewBrief(
        review_id="test-weiyanda-full",
        review_object_type="distribution_network_special_scheme",
        query="执行完整结构的停电施工方案合规审查，提取所有的违规发现点（Findings）"
    )
    
    # execute formal pipeline
    report, fact_packet = await controller.execute(
        brief=brief,
        document_path=doc_path
    )
    
    out_path = repo_root / "fixtures/supervision/停电施工方案-威彦达-全阵型实测审查结果.md"
    out_path.write_text(report, encoding="utf-8")
    
    print(f"Test completed. Detailed markdown report saved to:\n{out_path}")
    print(f"Report character length: {len(report)}")
    print(f"Total findings discovered by pipeline: {len(fact_packet.findings)}")

if __name__ == '__main__':
    asyncio.run(main())
