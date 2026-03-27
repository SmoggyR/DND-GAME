# AGENTS.md

## Project
A Disco Elysium-style text RPG in Python. No combat. KCD2 universe.

## Rules — never break these
- rules_engine.py must have ZERO API calls — pure Python logic only
- gemini_parser.py returns ONLY JSON, never prose
- grok_writer.py returns ONLY a prose string, never JSON
- All world truth lives in /state and /npcs JSON files
- Never store game state inside a model or chat history