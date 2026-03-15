"""Claude API client — 走 localhost:3456 proxy（OpenAI 兼容格式）"""

import re

from openai import OpenAI

from .config import load_config

_client = None
_config_cache = None

# Pre-compile regex patterns for code fence stripping
_RE_CODE_FENCE_START = re.compile(r"^```(?:json)?\s*\n?")
_RE_CODE_FENCE_END = re.compile(r"\n?```\s*$")


def get_client() -> OpenAI:
    global _client, _config_cache
    if _client is None:
        _config_cache = load_config()
        _client = OpenAI(
            base_url=_config_cache["proxy"]["base_url"],
            api_key=_config_cache["proxy"]["api_key"],
        )
    return _client


def get_model() -> str:
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache["proxy"]["model"]


def chat(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """簡單的 chat completion 包裝"""
    client = get_client()
    model = get_model()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        raise RuntimeError(f"Claude API 調用失敗: {e}") from e

    if not resp.choices:
        raise RuntimeError("Claude API 回傳空結果（沒有 choices）")
    return resp.choices[0].message.content


def chat_json(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """要求回傳 JSON 格式"""
    if system:
        system += "\n\n請用純 JSON 格式回覆，不要包含 markdown code block。"
    else:
        system = "請用純 JSON 格式回覆，不要包含 markdown code block。"
    raw = chat(prompt, system=system, temperature=temperature)
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = _RE_CODE_FENCE_START.sub("", cleaned)
        cleaned = _RE_CODE_FENCE_END.sub("", cleaned)
    return cleaned
