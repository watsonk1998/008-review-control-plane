from __future__ import annotations

import json
from pathlib import Path

from src.config.fastgpt import resolve_fastgpt_config
from src.config.llm import resolve_llm_config


def test_resolve_llm_config_from_env(monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL', 'https://example.com/v1')
    monkeypatch.setenv('LLM_API_KEY', 'secret')
    monkeypatch.setenv('LLM_MODEL', 'demo-model')
    monkeypatch.setenv('LLM_PROVIDER', 'demo-provider')

    config = resolve_llm_config()

    assert config.base_url == 'https://example.com/v1'
    assert config.api_key == 'secret'
    assert config.model == 'demo-model'
    assert config.provider == 'demo-provider'
    assert config.source == 'env'
    assert config.sanitized()['api_key'] == '***'


def test_resolve_llm_config_from_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_BASE_URL', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)

    payload = {
        'dashscope': {
            'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'api_key': 'sk-demo',
            'provider': 'dashscope',
            'models': {'chat': ['qwen3.5-plus']},
        }
    }
    config_path = tmp_path / 'century.json'
    config_path.write_text(json.dumps(payload), encoding='utf-8')
    monkeypatch.setenv('LLM_CONFIG_PATH', str(config_path))
    monkeypatch.setenv('LLM_CONFIG_PROFILE', 'dashscope')

    config = resolve_llm_config()

    assert config.base_url.endswith('/v1')
    assert config.api_key == 'sk-demo'
    assert config.model == 'qwen3.5-plus'
    assert config.source == 'credentials_file'


def test_resolve_fastgpt_config_from_file(tmp_path: Path, monkeypatch):
    monkeypatch.delenv('FASTGPT_BASE_URL', raising=False)
    monkeypatch.delenv('FASTGPT_API_URL', raising=False)
    monkeypatch.delenv('FASTGPT_API_KEY', raising=False)
    monkeypatch.delenv('FASTGPT_SEARCH_API_KEY', raising=False)

    payload = {
        'gbcs-fast': {
            'base_url': 'https://xtaiqa.jg-pm.com/api',
            'endpoint': '/v1/chat/completions',
            'api_key': 'api-secret',
            'headers': {'Authorization': 'Bearer search-secret'},
        }
    }
    config_path = tmp_path / 'gbcs-fast.json'
    config_path.write_text(json.dumps(payload), encoding='utf-8')
    monkeypatch.setenv('FASTGPT_CONFIG_PATH', str(config_path))

    config = resolve_fastgpt_config()

    assert config.base_url == 'https://xtaiqa.jg-pm.com/api'
    assert config.chat_url == 'https://xtaiqa.jg-pm.com/api/v1/chat/completions'
    assert config.api_key == 'api-secret'
    assert config.search_api_key == 'search-secret'
    assert config.source == 'credentials_file'
    sanitized = config.sanitized()
    assert sanitized['api_key'] == '***'
    assert sanitized['search_api_key'] == '***'


def test_resolve_fastgpt_config_from_env(monkeypatch):
    monkeypatch.setenv('FASTGPT_BASE_URL', 'https://fast.example.com/api')
    monkeypatch.setenv('FASTGPT_API_KEY', 'api-key')
    monkeypatch.setenv('FASTGPT_SEARCH_API_KEY', 'search-key')
    monkeypatch.delenv('FASTGPT_API_URL', raising=False)

    config = resolve_fastgpt_config()

    assert config.base_url == 'https://fast.example.com/api'
    assert config.chat_url == 'https://fast.example.com/api/v1/chat/completions'
    assert config.api_key == 'api-key'
    assert config.search_api_key == 'search-key'
    assert config.source == 'env'
