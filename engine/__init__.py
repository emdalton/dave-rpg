"""
engine/__init__.py — DAVE RPG Engine Package

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

The engine package contains all runtime logic for the DAVE RPG Engine:

    engine.config    — Runtime configuration (LLM backend, model, DB path, etc.)
    engine.db        — Database access layer (all SQL lives here)
    engine.context   — Context packet assembly for the three LLM passes
    engine.llm       — LLM backend abstraction (Claude / Ollama)
    engine.engine    — Main game loop (three-pass turn processing)

Typical entry point:

    from engine.engine import GameEngine
    from engine.db import Database

    with Database("modules/i_am_a_cat/i_am_a_cat.db") as db:
        engine = GameEngine(db, game_id=1)
        engine.run()
"""
