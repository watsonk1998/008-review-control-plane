from __future__ import annotations

from typing import Any
import httpx

from src.config.llm import LLMConfig, resolve_llm_config


class LLMGateway:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or resolve_llm_config()

    async def health_check(self) -> dict[str, Any]:
        response = await self.chat([
            {'role': 'system', 'content': 'You are a health check assistant.'},
            {'role': 'user', 'content': 'Reply with exactly: pong'},
        ], temperature=0)
        return {
            'available': True,
            'provider': self.config.provider,
            'model': self.config.model,
            'reply': response.get('content', ''),
            'config': self.config.sanitized(),
        }

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 1200) -> dict[str, Any]:
        url = self.config.base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': self.config.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.config.api_key}',
                },
            )
            response.raise_for_status()
            body = response.json()
        return {
            'content': body['choices'][0]['message']['content'],
            'raw': body,
            'usage': body.get('usage'),
        }

    async def summarize_chunks(self, query: str, chunks: list[dict[str, Any]], extra_instruction: str = '') -> dict[str, Any]:
        context = '\n\n'.join(
            f"[{index + 1}] {chunk.get('sourceLabel') or chunk.get('mode')}: {chunk.get('text', '')}"
            for index, chunk in enumerate(chunks[:8])
        )
        prompt = (
            '请严格基于提供的 chunks 回答。若 chunks 不足，请明确写出“不足以得出结论”。' +
            ('\n' + extra_instruction if extra_instruction else '') +
            f"\n\n问题：{query}\n\n可用上下文：\n{context}"
        )
        return await self.chat([
            {'role': 'system', 'content': '你是一个谨慎的工程知识整理助手。'},
            {'role': 'user', 'content': prompt},
        ])
