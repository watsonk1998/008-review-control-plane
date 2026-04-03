from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.routes.system import router as system_router
from src.routes.tasks import router as tasks_router
from src.routes.uploads import router as uploads_router


app = FastAPI(title='008 Review Control Plane API', version='0.1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        get_settings().web_origin,
        'http://localhost:3008',
        'http://127.0.0.1:3008',
        'http://localhost:3018',
        'http://127.0.0.1:3018',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(system_router)
app.include_router(tasks_router)
app.include_router(uploads_router)


@app.get('/')
async def root():
    return {
        'name': '008 Review Control Plane API',
        'role': 'DeepResearchAgent-compatible orchestration layer',
        'docs': '/docs',
    }
