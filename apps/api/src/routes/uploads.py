from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.config.settings import get_settings
from src.domain.models import SourceDocumentRef

router = APIRouter(prefix='/api/uploads', tags=['uploads'])

_ALLOWED_SUFFIXES = {'.docx', '.pdf', '.md', '.txt'}


@router.post('/documents')
async def upload_document(file: UploadFile = File(...)):
    file_name = Path(file.filename or 'document').name
    suffix = Path(file_name).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f'Unsupported file type: {suffix or "unknown"}')

    ref_id = uuid.uuid4().hex
    upload_dir = get_settings().uploads_dir / ref_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / file_name
    with destination.open('wb') as output:
        shutil.copyfileobj(file.file, output)

    return SourceDocumentRef(
        refId=ref_id,
        sourceType='upload',
        fileName=file_name,
        fileType=suffix.lstrip('.'),
        storagePath=str(destination),
        displayName=file_name,
        mediaType=file.content_type,
        uploadedAt=datetime.now(timezone.utc),
    ).model_dump(mode='json')
