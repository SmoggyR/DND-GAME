import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from gemini_parser import GeminiParserError, parse_player_text
from grok_writer import GrokWriterError, write_prose
from rules_engine import RulesEngineError, load_scene, resolve_action


BASE_DIR = Path(__file__).resolve().parent
STATE_DIR = BASE_DIR / "state"
LOGS_DIR = BASE_DIR / "logs"
TRANSCRIPT_PATH = LOGS_DIR / "transcript.jsonl"

EXIT_COMMANDS = {"quit", "exit", "q"}


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _load_player() -> Dict[str, Any]:
    return _load_json(STATE_DIR / "player.json")


def _resolve_scene_id(player_state: Dict[str, Any]) -> str:
    scene_id = player_state.get("current_location")
    return str(scene_id) if scene_id else "tavern_main"


def _resolve_npc_id(scene_data: Dict[str, Any], target_npc: Any) -> str:
    npcs_present = scene_data.get("npcs_present", [])
    if not isinstance(npcs_present, list) or not npcs_present:
        raise RulesEngineError("Scene has no npcs_present to target.")

    requested = str(target_npc).strip() if target_npc is not None else ""
    if not requested:
        return str(npcs_present[0])

    requested_lower = requested.lower()
    for npc_id in npcs_present:
        npc_id_str = str(npc_id)
        if npc_id_str.lower() == requested_lower:
            return npc_id_str

    return str(npcs_present[0])


def _build_scene_packet(
    player_state: Dict[str, Any],
    parsed_action: Dict[str, Any],
    resolved_action: Dict[str, Any],
    player_text: str,
    turn_index: int,
) -> Dict[str, Any]:
    return {
        "turn_index": turn_index,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "player_text": player_text,
        "player": {
            "id": player_state.get("id"),
            "name": player_state.get("name"),
            "current_location": player_state.get("current_location"),
            "status": player_state.get("status", {}),
            "skills": player_state.get("skills", {}),
        },
        "parsed_action": parsed_action,
        "resolved_action": resolved_action,
    }


def _append_transcript(entry: Dict[str, Any]) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with TRANSCRIPT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_turn_loop() -> None:
    print("Type your action. Use 'quit' to exit.")
    turn_index = 1

    while True:
        player_text = input("\n> ").strip()
        if not player_text:
            continue
        if player_text.lower() in EXIT_COMMANDS:
            print("Session ended.")
            break

        transcript_entry: Dict[str, Any] = {
            "turn_index": turn_index,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "player_text": player_text,
            "ok": False,
        }

        try:
            player_state = _load_player()
            scene_id = _resolve_scene_id(player_state)
            scene_data = load_scene(scene_id)

            parsed_action = parse_player_text(player_text)
            npc_id = _resolve_npc_id(scene_data, parsed_action.get("target_npc"))
            action_family = str(parsed_action.get("intent_family", "")).strip()

            resolved_action = resolve_action(
                action_family=action_family,
                npc_id=npc_id,
                scene_id=scene_id,
                action_payload=parsed_action,
            )

            scene_packet = _build_scene_packet(
                player_state=player_state,
                parsed_action=parsed_action,
                resolved_action=resolved_action,
                player_text=player_text,
                turn_index=turn_index,
            )

            prose = write_prose(scene_packet)
            print(f"\n{prose}\n")

            transcript_entry.update(
                {
                    "ok": True,
                    "scene_id": scene_id,
                    "parsed_action": parsed_action,
                    "resolved_action": resolved_action,
                    "scene_packet": scene_packet,
                    "prose": prose,
                }
            )
        except (GeminiParserError, RulesEngineError, GrokWriterError, OSError, ValueError) as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            print(f"\n[Error] {error_text}\n")
            transcript_entry["error"] = error_text
        finally:
            _append_transcript(transcript_entry)
            turn_index += 1


if __name__ == "__main__":
    run_turn_loop()

