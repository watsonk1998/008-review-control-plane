import asyncio
import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)

async def _post_callback(url: str, payload: dict[str, Any]):
    logger.info(f"External callback FIRING to {url} with payload: {payload}")
    try:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.post(url, json=payload, timeout=15.0)
            logger.info(f"External callback to {url} responded: status={res.status_code}, body={res.text[:500]}")
            res.raise_for_status()
            logger.info(f"External callback to {url} succeeded.")
    except Exception as e:
        logger.error(f"External callback to {url} failed: {e}", exc_info=True)

async def trigger_task_created_callback(task_id: str, file_name: str, ext_ctx):
    if ext_ctx is None or not ext_ctx.callBackUrl:
        logger.info(f"Skipping task_created callback: ext_ctx={ext_ctx}")
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
        logger.info(f"Skipping task_status callback: ext_ctx={ext_ctx}")
        return
    base_url = ext_ctx.callBackUrl.rstrip('/')
    url = f"{base_url}/api/wekb-operate/constructionPlanReview/updateReportStatus"
    
    # Map internal status to generateStatus
    mapped_status = "2" if status == 'succeeded' else "3" 
    
    payload = {
        "pkId": task_id,
        "generateStatus": mapped_status,
    }
    logger.info(f"trigger_task_status_callback: task_id={task_id}, internal_status={status}, mapped={mapped_status}")
    await _post_callback(url, payload)
