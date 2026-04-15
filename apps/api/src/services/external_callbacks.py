import asyncio
import logging
import sys
from typing import Any
import httpx

# Force logging to stdout at INFO level for this module
logging.basicConfig(level=logging.INFO, stream=sys.stderr, force=False)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

async def _post_callback(url: str, payload: dict[str, Any]):
    print(f"[CALLBACK] FIRING to {url} with payload: {payload}", flush=True)
    try:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.post(url, json=payload, timeout=15.0)
            print(f"[CALLBACK] Response from {url}: status={res.status_code}, body={res.text[:500]}", flush=True)
            res.raise_for_status()
            print(f"[CALLBACK] SUCCESS: {url}", flush=True)
    except Exception as e:
        print(f"[CALLBACK] FAILED: {url} error={e}", flush=True)
        import traceback
        traceback.print_exc()

async def trigger_task_created_callback(task_id: str, file_name: str, ext_ctx):
    if ext_ctx is None or not ext_ctx.callBackUrl:
        print(f"[CALLBACK] Skipping task_created: ext_ctx={ext_ctx}", flush=True)
        return
    base_url = ext_ctx.callBackUrl.rstrip('/')
    url = f"{base_url}/api/wekb-operate/constructionPlanReview/submit"
    payload = {
        "pkId": task_id,
        "generateStatus": "1",
        "fileName": file_name,
        "agentId": ext_ctx.agentId,
        "userId": ext_ctx.userId,
        "tenantId": ext_ctx.tenantId,
    }
    await _post_callback(url, payload)

async def trigger_task_status_callback(task_id: str, status: str, ext_ctx):
    if ext_ctx is None or not ext_ctx.callBackUrl:
        print(f"[CALLBACK] Skipping task_status: ext_ctx={ext_ctx}", flush=True)
        return
    base_url = ext_ctx.callBackUrl.rstrip('/')
    url = f"{base_url}/api/wekb-operate/constructionPlanReview/updateReviewStatus"
    
    # Map internal status to generateStatus
    mapped_status = "2" if status == 'succeeded' else "3" 
    
    payload = {
        "pkId": task_id,
        "generateStatus": mapped_status,
    }
    print(f"[CALLBACK] trigger_task_status_callback: task_id={task_id}, status={status} -> generateStatus={mapped_status}", flush=True)
    await _post_callback(url, payload)
