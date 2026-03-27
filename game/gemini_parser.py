import json
import os
from typing import Any, Dict, Optional
from urllib import error, request

from dotenv import load_dotenv


SYSTEM_PROMPT = "You are an intent parser for a text RPG. The player typed something. Convert it into a JSON object with exactly these fields: intent_family (one of: speak, ask, observe, flirt, threaten, accuse, leave, self_action), target_npc (string or null), topic (string or null), tone (one word: casual/aggressive/nervous/curious/friendly), skill_hint (one of: persuasion, deception, insight, intimidation, scholarship, or null). Return ONLY valid JSON. No explanation, no markdown, no extra text."
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


def _get_api_key() -> Optional[str]:
    load_dotenv()
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _call_gemini(player_text: str, api_key: str) -> Optional[str]:
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": player_text}]}],
    }
    req = request.Request(
        url=f"{GEMINI_API_URL}?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except (error.HTTPError, error.URLError):
        return None

    try:
        response_json = json.loads(raw)
        return response_json["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def parse_player_input(player_text: str) -> Optional[Dict[str, Any]]:
    api_key = _get_api_key()
    if not api_key:
        return None

    for _ in range(2):
        model_text = _call_gemini(player_text, api_key)
        if not model_text:
            continue
        try:
            parsed = json.loads(model_text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


if __name__ == "__main__":
    result = parse_player_input("I ask the innkeeper about the missing miller")
    print(result)

