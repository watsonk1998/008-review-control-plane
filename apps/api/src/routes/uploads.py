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
_ALLOWED_MEDIA_TYPES = {
    '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
    '.pdf': {'application/pdf'},
    '.md': {'text/markdown', 'text/plain', 'text/x-markdown'},
    '.txt': {'text/plain'},
}


def _normalize_content_type(raw: str | None) -> str | None:
    if not raw:
        return None
    normalized = raw.split(';', 1)[0].strip().lower()
    return normalized or None


def _upload_error(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=400, detail={'code': code, 'message': message})


@router.post('/documents')
async def upload_document(file: UploadFile = File(...)):
    raw_name = (file.filename or '').strip()
    if not raw_name:
        raise _upload_error('invalid_file_name', 'Invalid upload filename: missing file name')
    file_name = Path(raw_name).name
    if not file_name.strip():
        raise _upload_error('invalid_file_name', 'Invalid upload filename: missing file name')
    suffix = Path(file_name).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise _upload_error('unsupported_file_type', f'Unsupported file type: {suffix or "unknown"}')
    content_type = _normalize_content_type(file.content_type)
    if content_type is None:
        raise _upload_error('missing_content_type', f'Missing content type for {suffix} upload')
    if content_type not in _ALLOWED_MEDIA_TYPES[suffix]:
        raise _upload_error('content_type_mismatch', f'Unexpected content type for {suffix} upload: {content_type}')

    ref_id = uuid.uuid4().hex
    upload_dir = get_settings().uploads_dir / ref_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / file_name
    await file.seek(0)
    with destination.open('wb') as output:
        shutil.copyfileobj(file.file, output)

    payload = SourceDocumentRef(
        refId=ref_id,
        sourceType='upload',
        fileName=file_name,
        fileType=suffix.lstrip('.'),
        storagePath=str(destination),
        displayName=file_name,
        mediaType=content_type,
        uploadedAt=datetime.now(timezone.utc),
    ).model_dump(mode='json')
    payload.update(
        {
            'file_id': payload['refId'],
            'file_name': payload['fileName'],
            'file_type': payload['fileType'],
            'display_name': payload['displayName'],
            'uploaded_at': payload['uploadedAt'],
        }
    )
    return payload
