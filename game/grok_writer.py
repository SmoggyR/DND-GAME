import json
import os
from pathlib import Path
from typing import Any, Dict
from urllib import error, request


DEFAULT_GROK_API_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_GROK_MODEL = "grok-3-mini"
SYSTEM_PROMPT = (
    "You are a narrative writer for a Disco Elysium-style text RPG set in the KCD2 universe. "
    "Given a scene packet, write immersive prose for the current moment. "
    "Return prose only."
)


class GrokWriterError(Exception):
    """Raised when Grok writing fails."""


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _get_grok_api_key() -> str:
    _load_env_file(Path(".env"))
    api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    if not api_key:
        raise GrokWriterError(
            "Missing Grok API key. Set GROK_API_KEY (or XAI_API_KEY) in .env."
        )
    return api_key


def _extract_prose(response_json: Dict[str, Any]) -> str:
    choices = response_json.get("choices", [])
    if not choices:
        raise GrokWriterError("Grok response has no choices.")

    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        prose = content.strip()
        if prose:
            return prose
    elif isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_value = item.get("text", "")
                if text_value:
                    parts.append(str(text_value))
        prose = "\n".join(parts).strip()
        if prose:
            return prose

    raise GrokWriterError("Grok response did not contain prose text.")


def write_prose(scene_packet: Dict[str, Any]) -> str:
    api_key = _get_grok_api_key()
    api_url = os.getenv("GROK_API_URL", DEFAULT_GROK_API_URL)
    model = os.getenv("GROK_MODEL", DEFAULT_GROK_MODEL)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(scene_packet, ensure_ascii=False)},
        ],
        "temperature": 0.7,
    }

    req = request.Request(
        url=api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise GrokWriterError(f"Grok API HTTP error: {exc.code} {details}") from exc
    except error.URLError as exc:
        raise GrokWriterError(f"Grok API connection error: {exc}") from exc

    response_json = json.loads(raw)
    return _extract_prose(response_json)

