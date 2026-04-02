from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os

DEFAULT_FASTGPT_CONFIG_PATH = Path.home() / 'tools' / 'from-obsidian' / 'AI' / 'config' / 'gbcs-fast.json'


@dataclass
class FastGPTConfig:
    base_url: str
    chat_url: str
    api_key: str
    search_api_key: str
    source: str
    config_path: str | None = None

    def sanitized(self) -> dict:
        payload = asdict(self)
        payload['api_key'] = '***' if self.api_key else ''
        payload['search_api_key'] = '***' if self.search_api_key else ''
        return payload


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return ''


def _normalize_base_from_chat_url(raw: str) -> str:
    text = raw.strip().rstrip('/')
    for suffix in ('/api/v1/chat/completions', '/v1/chat/completions', '/chat/completions'):
        if text.endswith(suffix):
            return text[: -len(suffix)]
    return text


def resolve_fastgpt_config() -> FastGPTConfig:
    env_chat = _first_non_empty(os.getenv('FASTGPT_API_URL'))
    env_base = _first_non_empty(os.getenv('FASTGPT_BASE_URL'))
    env_api_key = _first_non_empty(os.getenv('FASTGPT_API_KEY'))
    env_search_key = _first_non_empty(os.getenv('FASTGPT_SEARCH_API_KEY'), env_api_key)

    if env_api_key and (env_chat or env_base):
        base_url = _normalize_base_from_chat_url(env_chat or env_base)
        chat_url = env_chat.rstrip('/') if env_chat else base_url.rstrip('/') + '/v1/chat/completions'
        return FastGPTConfig(
            base_url=base_url.rstrip('/'),
            chat_url=chat_url,
            api_key=env_api_key,
            search_api_key=env_search_key,
            source='env',
        )

    config_path = Path(os.getenv('FASTGPT_CONFIG_PATH', str(DEFAULT_FASTGPT_CONFIG_PATH))).expanduser()
    if not config_path.exists():
        raise FileNotFoundError(f'FastGPT config file not found: {config_path}')
    payload = json.loads(config_path.read_text())
    profile = payload.get('gbcs-fast')
    if not isinstance(profile, dict):
        raise KeyError('gbcs-fast profile missing from FastGPT config')

    raw_base_url = str(profile.get('base_url') or '').rstrip('/')
    endpoint = str(profile.get('endpoint') or '/v1/chat/completions')
    chat_url = raw_base_url + endpoint if endpoint.startswith('/') else raw_base_url + '/' + endpoint
    base_url = _normalize_base_from_chat_url(raw_base_url)
    headers = profile.get('headers') or {}
    header_token = str(headers.get('Authorization') or '').replace('Bearer ', '').strip()
    api_key = str(profile.get('api_key') or '').strip()
    search_key = _first_non_empty(os.getenv('FASTGPT_SEARCH_API_KEY'), header_token, api_key)
    if not raw_base_url or not api_key:
        raise ValueError(f'Incomplete FastGPT config in {config_path}')
    return FastGPTConfig(
        base_url=base_url.rstrip('/'),
        chat_url=chat_url.rstrip('/'),
        api_key=api_key,
        search_api_key=search_key,
        source='credentials_file',
        config_path=str(config_path),
    )


DEFAULT_DATASET_REGISTRY = {
    'gb_national': {
        'datasetId': '69842ce095a6ce02e8055b98',
        'label': '国家标准 GB/GBT',
    },
    'building_municipal': {
        'datasetId': '6984435295a6ce02e80696a1',
        'label': '房建与市政 JG/JGJ/CJJ',
    },
    'petrochemical': {
        'datasetId': '698444f395a6ce02e806baeb',
        'label': '石油石化化工',
    },
    'laws_regulations': {
        'datasetId': '69ac6551c5c0bdd8e039b120',
        'label': '法律法规',
    },
}
