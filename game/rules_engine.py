import json
from pathlib import Path
from typing import Any, Dict


BASE_DIR = Path(__file__).resolve().parent
STATE_DIR = BASE_DIR / "state"
NPCS_DIR = BASE_DIR / "npcs"


def load_world_flags() -> Dict[str, Any]:
    path = STATE_DIR / "world_flags.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_npc_dossier(npc_id: str) -> Dict[str, Any]:
    path = NPCS_DIR / f"{npc_id}.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_scene(scene_id: str) -> Dict[str, Any]:
    path = STATE_DIR / f"{scene_id}.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_action(intent_family: str, npc_id: str, scene_id: str) -> Dict[str, Any]:
    scene = load_scene(scene_id)
    npc = load_npc_dossier(npc_id)

    allowed_action_families = scene.get("allowed_action_families", [])
    if intent_family not in allowed_action_families:
        return {
            "allowed": False,
            "npc_id": npc_id,
            "intent_family": intent_family,
            "reason": "intent_not_allowed_in_scene",
        }

    if not npc.get("speakable", False):
        return {
            "allowed": False,
            "npc_id": npc_id,
            "intent_family": intent_family,
            "reason": "npc_not_speakable",
        }

    return {
        "allowed": True,
        "npc_id": npc_id,
        "intent_family": intent_family,
        "reason": "ok",
    }


if __name__ == "__main__":
    result = resolve_action("ask", "innkeeper", "tavern_main")
    print(result)

