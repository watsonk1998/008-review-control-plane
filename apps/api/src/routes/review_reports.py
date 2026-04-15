from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.domain.models import ReviewReportFeedbackRequest, ReviewReportFeedbackResponse
from src.main_dependencies import get_task_service

router = APIRouter(prefix='/api/review-reports', tags=['review-reports'])


@router.post('/{report_id}/feedback')
async def submit_review_report_feedback(report_id: str, request: ReviewReportFeedbackRequest):
    service = get_task_service()
    try:
        stored = service.submit_report_feedback(
            report_id=report_id,
            feedback_type=request.feedback_type,
            comment=request.comment,
            source=request.source,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail={'code': 'report_not_found', 'message': 'Report not found'}) from None
    return ReviewReportFeedbackResponse(
        report_id=report_id,
        feedback_id=stored['id'],
    ).model_dump(mode='json')
