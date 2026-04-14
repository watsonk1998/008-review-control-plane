import asyncio
import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)

async def _post_callback(url: str, payload: dict[str, Any]):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=5.0)
            res.raise_for_status()
            logger.info(f"External callback to {url} succeeded.")
    except Exception as e:
        logger.error(f"External callback to {url} failed: {e}")

def trigger_task_created_callback(task_id: str, file_name: str, ext_ctx):
    if ext_ctx is None or not ext_ctx.callBackUrl:
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
    asyncio.create_task(_post_callback(url, payload))

def trigger_task_status_callback(task_id: str, status: str, ext_ctx):
    if ext_ctx is None or not ext_ctx.callBackUrl:
        return
    base_url = ext_ctx.callBackUrl.rstrip('/')
    # Assuming updateStatus for now; will consult user if needed, or maybe it is the same submit URL.
    # We use updateStatus here based on the planned architecture.
    url = f"{base_url}/api/wekb-operate/constructionPlanReview/updateReportStatus"
    
    # Map internal status to generateStatus
    mapped_status = "2" if status == 'succeeded' else "3" 
    
    payload = {
        "pkId": task_id,
        "generateStatus": mapped_status,
    }
    asyncio.create_task(_post_callback(url, payload))
