"""
engine/__main__.py — Entry point for `python -m engine`

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Allows the engine to be launched as a module:
    DAVE_DB_PATH=path/to/db python -m engine
"""

from engine.engine import main

main()
