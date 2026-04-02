from __future__ import annotations

from urllib.parse import urlparse
import json

import httpx
import websockets


class DeepTutorAdapter:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    async def health_check(self) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.base_url + '/api/v1/system/status')
            response.raise_for_status()
            body = response.json()
        return {'available': True, 'mode': 'http+websocket', 'raw': body}

    async def ask_knowledge_question(self, query: str, *, kb_name: str = '', enable_rag: bool = False, enable_web_search: bool = False) -> dict:
        return await self._chat(
            query,
            kb_name=kb_name,
            enable_rag=enable_rag,
            enable_web_search=enable_web_search,
        )

    async def ask_with_context(self, query: str, context_chunks: list[dict]) -> dict:
        context = '\n\n'.join(
            f"[{index + 1}] {chunk.get('sourceLabel') or chunk.get('mode')}: {chunk.get('text', '')}"
            for index, chunk in enumerate(context_chunks[:8])
        )
        message = (
            '请仅依据下面提供的工程知识上下文进行解释，不要虚构未给出的依据。'
            f"\n\n上下文：\n{context}\n\n问题：{query}"
        )
        return await self._chat(message, kb_name='', enable_rag=False, enable_web_search=False)

    async def _chat(self, message: str, *, kb_name: str, enable_rag: bool, enable_web_search: bool) -> dict:
        parsed = urlparse(self.base_url)
        ws_scheme = 'wss' if parsed.scheme == 'https' else 'ws'
        ws_url = f"{ws_scheme}://{parsed.netloc}/api/v1/chat"
        transcript: list[dict] = []
        async with websockets.connect(ws_url, max_size=10_000_000) as websocket:
            await websocket.send(json.dumps({
                'message': message,
                'session_id': None,
                'kb_name': kb_name,
                'enable_rag': enable_rag,
                'enable_web_search': enable_web_search,
            }, ensure_ascii=False))
            while True:
                raw = await websocket.recv()
                payload = json.loads(raw)
                transcript.append(payload)
                if payload.get('type') == 'result':
                    return {
                        'answer': payload.get('content', ''),
                        'sessionId': next((item.get('session_id') for item in transcript if item.get('type') == 'session'), None),
                        'sources': next((item for item in transcript if item.get('type') == 'sources'), None),
                        'transcript': transcript,
                    }
                if payload.get('type') == 'error':
                    raise RuntimeError(payload.get('message', 'DeepTutor websocket error'))
