from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os

DEFAULT_LLM_CONFIG_PATH = Path.home() / 'tools' / 'from-obsidian' / 'AI' / 'config' / 'century.json'
DEFAULT_LLM_PROFILE = 'dashscope'
DEFAULT_LLM_MODEL = 'qwen3.5-plus'


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    provider: str
    source: str
    profile: str

    def sanitized(self) -> dict:
        payload = asdict(self)
        payload['api_key'] = '***' if self.api_key else ''
        return payload


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return ''


def resolve_llm_config() -> LLMConfig:
    env_base = _first_non_empty(os.getenv('LLM_BASE_URL'), os.getenv('OPENAI_BASE_URL'))
    env_key = _first_non_empty(os.getenv('LLM_API_KEY'), os.getenv('OPENAI_API_KEY'))
    env_model = _first_non_empty(os.getenv('LLM_MODEL'), os.getenv('OPENAI_MODEL'))
    env_provider = _first_non_empty(os.getenv('LLM_PROVIDER'))
    if env_base and env_key:
        return LLMConfig(
            base_url=env_base.rstrip('/'),
            api_key=env_key,
            model=env_model or DEFAULT_LLM_MODEL,
            provider=env_provider or 'env-openai-compatible',
            source='env',
            profile=os.getenv('LLM_CONFIG_PROFILE', DEFAULT_LLM_PROFILE),
        )

    config_path = Path(os.getenv('LLM_CONFIG_PATH', str(DEFAULT_LLM_CONFIG_PATH))).expanduser()
    profile = os.getenv('LLM_CONFIG_PROFILE', DEFAULT_LLM_PROFILE)
    if not config_path.exists():
        raise FileNotFoundError(f'LLM config file not found: {config_path}')

    payload = json.loads(config_path.read_text())
    profile_data = payload.get(profile)
    if not isinstance(profile_data, dict):
        raise KeyError(f'LLM profile not found: {profile}')

    models = profile_data.get('models')
    model = env_model or DEFAULT_LLM_MODEL
    if isinstance(models, dict):
        chat_models = models.get('chat')
        if isinstance(chat_models, list) and chat_models:
            model = env_model or str(chat_models[0])
        elif isinstance(chat_models, str):
            model = env_model or chat_models
    elif isinstance(models, list) and models:
        model = env_model or str(models[0])

    base_url = str(profile_data.get('base_url', '')).rstrip('/')
    api_key = str(profile_data.get('api_key', '')).strip()
    if not base_url or not api_key:
        raise ValueError(f'Incomplete LLM config in {config_path}#{profile}')

    return LLMConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        provider=str(profile_data.get('provider') or profile),
        source='credentials_file',
        profile=profile,
    )
