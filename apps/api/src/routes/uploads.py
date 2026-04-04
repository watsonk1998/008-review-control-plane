from __future__ import annotations

from datetime import datetime, timezone
import mimetypes
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.config.settings import get_settings
from src.domain.models import SourceDocumentRef

router = APIRouter(prefix='/api/uploads', tags=['uploads'])

_ALLOWED_SUFFIXES = {'.docx', '.pdf', '.md', '.txt'}
_ALLOWED_MEDIA_TYPES = {
    '.docx': {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    },
    '.pdf': {'application/pdf'},
    '.md': {'text/markdown', 'text/plain', 'text/x-markdown'},
    '.txt': {'text/plain'},
}


@router.post('/documents')
async def upload_document(file: UploadFile = File(...)):
    file_name = Path(file.filename or '').name.strip()
    if not file_name:
        raise HTTPException(status_code=400, detail='Invalid upload filename: missing file name')

    suffix = Path(file_name).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f'Unsupported file type: {suffix or "unknown"}')

    media_type = _resolve_media_type(suffix, file.content_type)
    ref_id = uuid.uuid4().hex
    upload_dir = get_settings().uploads_dir / ref_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / file_name
    await file.seek(0)
    with destination.open('wb') as output:
        shutil.copyfileobj(file.file, output)

    return SourceDocumentRef(
        refId=ref_id,
        sourceType='upload',
        fileName=file_name,
        fileType=suffix.lstrip('.'),
        storagePath=str(destination),
        displayName=file_name,
        mediaType=media_type,
        uploadedAt=datetime.now(timezone.utc),
    ).model_dump(mode='json')


def _resolve_media_type(suffix: str, raw_content_type: str | None) -> str:
    normalized = (raw_content_type or '').split(';', 1)[0].strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail=f'Missing content type for {suffix} upload')

    allowed = _ALLOWED_MEDIA_TYPES[suffix]
    guessed = (mimetypes.guess_type(f'upload{suffix}')[0] or '').lower()
    if normalized not in allowed and normalized != guessed:
        raise HTTPException(status_code=400, detail=f'Unexpected content type for {suffix} upload: {normalized}')

    return guessed or normalized
