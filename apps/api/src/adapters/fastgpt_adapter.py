from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import time

import httpx

from src.config.fastgpt import FastGPTConfig, resolve_fastgpt_config


class FastGPTResponseParseError(RuntimeError):
    pass


@dataclass
class FastChunk:
    text: str
    raw: dict[str, Any]
    score: float | None
    sourceLabel: str | None
    mode: str


class FastGPTAdapter:
    def __init__(self, config: FastGPTConfig | None = None):
        self.config = config or resolve_fastgpt_config()

    async def health_check(self) -> dict[str, Any]:
        return {
            'available': True,
            'mode': 'http',
            'config': self.config.sanitized(),
        }

    async def search_dataset_chunks(
        self,
        dataset_id: str,
        query: str,
        *,
        limit: int = 5000,
        similarity: float = 0.3,
        search_mode: str = 'mixedRecall',
        using_rerank: bool = True,
    ) -> dict[str, Any]:
        payload = {
            'datasetId': dataset_id,
            'text': query,
            'limit': limit,
            'similarity': similarity,
            'searchMode': search_mode,
            'usingReRank': using_rerank,
            'datasetSearchUsingExtensionQuery': False,
        }
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                self.config.base_url.rstrip('/') + '/core/dataset/searchTest',
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.config.search_api_key}',
                },
            )
            response.raise_for_status()
            body = response.json()
        items = body.get('data', {}).get('list', [])
        chunks = [self._normalize_chunk(item, mode='dataset') for item in items]
        return {
            'mode': 'dataset',
            'datasetId': dataset_id,
            'collectionId': None,
            'query': query,
            'chunks': [chunk.__dict__ for chunk in chunks],
            'raw': body,
            'meta': {
                'count': len(chunks),
                'searchMode': body.get('data', {}).get('searchMode'),
                'similarity': body.get('data', {}).get('similarity'),
                'usingReRank': body.get('data', {}).get('usingReRank'),
            },
            'durationMs': round((time.perf_counter() - start) * 1000),
        }

    async def search_collection_chunks(self, collection_id: str, query: str, dataset_id: str | None = None) -> dict[str, Any]:
        payload = {
            'stream': False,
            'detail': False,
            'variables': {'collectionId': collection_id},
            'messages': [{'role': 'user', 'content': query}],
        }
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                self.config.chat_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.config.api_key}',
                },
            )
            response.raise_for_status()
            body = response.json()
        content = body.get('choices', [{}])[0].get('message', {}).get('content', '')
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise FastGPTResponseParseError(
                f"FastGPT collection workflow did not return JSON. prefix={content[:160]!r}"
            ) from exc
        if not isinstance(parsed, list):
            raise FastGPTResponseParseError('FastGPT collection workflow returned non-list JSON payload')
        chunks = [self._normalize_chunk(item, mode='collection') for item in parsed]
        inferred_dataset = dataset_id or (parsed[0].get('datasetId') if parsed else None)
        return {
            'mode': 'collection',
            'datasetId': inferred_dataset,
            'collectionId': collection_id,
            'query': query,
            'chunks': [chunk.__dict__ for chunk in chunks],
            'raw': body,
            'meta': {'count': len(chunks)},
            'durationMs': round((time.perf_counter() - start) * 1000),
        }

    def _normalize_chunk(self, item: dict[str, Any], *, mode: str) -> FastChunk:
        score_value = None
        score = item.get('score')
        if isinstance(score, list) and score:
            first = score[0]
            if isinstance(first, dict):
                score_value = first.get('value')
        elif isinstance(score, (int, float)):
            score_value = float(score)
        return FastChunk(
            text=str(item.get('q') or item.get('text') or ''),
            raw=item,
            score=score_value,
            sourceLabel=item.get('sourceName') or item.get('sourceLabel'),
            mode=mode,
        )
