# DAVE RPG Engine — Configuration Reference

*Last updated: 2026-05-29. The authoritative source for default values is `engine/config.py`.*

All configuration is done through environment variables. There are no command-line flags; the engine reads its settings from the environment at startup. This makes it easy to run different modules or backends without modifying any source files.

---

## Running the engine

The cleanest way to run is to export your API key once per shell session and then use the `DAVE_*` variables inline per run:

```bash
export ANTHROPIC_API_KEY=your_key_here
DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine
```

For the Meryton module, also set the game ID:

```bash
DAVE_GAME_ID=2 DAVE_DB_PATH=modules/Meryton/meryton.db python3 -m engine
```

---

## Logging and output verbosity

By default the engine logs at INFO level to stderr. This is generally the right level for play sessions, but it does include some API transport messages from the `httpx` library that can clutter the terminal output.

```bash
# Default — INFO level; some httpx transport messages visible
DAVE_DB_PATH=... python3 -m engine

# Quiet — WARNING and above only; suppresses most httpx and engine INFO messages
DAVE_LOG_LEVEL=WARNING DAVE_DB_PATH=... python3 -m engine

# Debug — full pass-level detail including raw prompts and LLM responses
DAVE_LOG_LEVEL=DEBUG DAVE_DB_PATH=... python3 -m engine
```

**Note on httpx messages:** The Anthropic SDK uses `httpx` internally, and httpx INFO messages (connection details, request timing) appear on stderr alongside game output. `DAVE_LOG_LEVEL=WARNING` suppresses them. A cleaner solution — routing engine logs to a file and leaving only game prose on stdout — is planned as §7 of the pending work queue. Until then, `WARNING` is the practical choice for play sessions.

---

## Environment variable reference

### Required

| Variable | Description |
|---|---|
| `DAVE_DB_PATH` | Path to the SQLite module database. Relative to the working directory. No default — the engine will use `game.db` if unset, which almost certainly does not exist. |
| `ANTHROPIC_API_KEY` | Anthropic API key. Required when using the Claude backend. Never put this in source files. |

### LLM backend

| Variable | Default | Description |
|---|---|---|
| `DAVE_LLM_BACKEND` | `claude` | Which LLM backend to use. `claude` uses the Anthropic API; `ollama` uses a local model via the Ollama HTTP API. The Ollama backend is currently a stub. |
| `DAVE_CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model string. Use `claude-haiku-4-5-20251001` for faster, cheaper runs at some quality cost. |
| `DAVE_CLAUDE_MAX_TOKENS` | `2048` | Maximum tokens the model may generate per call. |
| `DAVE_OLLAMA_BASE_URL` | `http://localhost:11434` | URL of the Ollama HTTP API. |
| `DAVE_OLLAMA_MODEL` | `mistral` | Model name as registered in Ollama. |
| `DAVE_OLLAMA_TIMEOUT` | `120` | Timeout in seconds for Ollama requests. Increase on slow hardware. |

### Engine tuning

| Variable | Default | Description |
|---|---|---|
| `DAVE_PASS1_RECENT_ACTIONS` | `5` | Number of recent action log entries included in Pass 1 context. More context helps disambiguation; fewer saves tokens. |
| `DAVE_PASS2_MAX_LOCATION_DETAILS` | `10` | Maximum generated location details included per location in Pass 2 context. |
| `DAVE_PASS2_MAX_ITEMS` | `12` | Maximum visible items included per location in Pass 2 context. |
| `DAVE_LLM_MAX_RETRIES` | `3` | Retry attempts when an LLM call returns malformed JSON before giving up. |
| `DAVE_ACTION_LOG_MAX_ROWS` | `50` | Maximum action log rows retained before pruning. Keeps long sessions from accumulating unboundedly. |
| `DAVE_INVOLUNTARY_MAX_PROB` | `0.25` | Per-turn probability cap for involuntary events (hairball, sneeze, etc.). Prevents a maxed-out state from making the event certain every turn. |
| `DAVE_WANDER_SLEEPINESS_THRESHOLD` | `0.60` | Sleepiness value at or above which an NPC's wander roll is suppressed. 0.0 disables the suppression. |
| `DAVE_ACTIVITY_AUTO_CLEAR_CONFIDENCE` | `0.60` | Confidence threshold above which an expired non-renewable activity is auto-cleared by the engine. Activities below this threshold are only cleared by Pass 2 explicitly. Set to `1.01` to disable auto-clearing entirely. |
| `DAVE_LOG_LEVEL` | `INFO` | Python logging level. `DEBUG` shows raw prompts and LLM responses. `WARNING` suppresses most informational output. |

### Database

| Variable | Default | Description |
|---|---|---|
| `DAVE_DB_PATH` | `game.db` | Path to the SQLite database file for the module you want to run. |
| `DAVE_GAME_ID` | `1` | Game record ID within the database. Most single-module databases use ID 1. The Meryton module uses ID 2. |

---

## Test suite configuration

The test suite has its own env vars on top of the engine ones. See [test_suite.md](test_suite.md) for full test suite documentation.

| Variable | Default | Description |
|---|---|---|
| `DAVE_EVAL_MODEL` | `claude-haiku-4-5-20251001` | Model used for LLM-as-judge evaluation in Tier 3 tests. Haiku is the default for cost efficiency; swap for Sonnet if judge quality is insufficient. |

To run Tier 2 or Tier 3 tests you also need `ANTHROPIC_API_KEY` set.

---

## Typical session setups

**Standard play (clean terminal, minimal noise):**
```bash
export ANTHROPIC_API_KEY=your_key_here
DAVE_LOG_LEVEL=WARNING DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine
```

**Development (see what the engine is doing):**
```bash
DAVE_LOG_LEVEL=INFO DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine
```

**Debugging a specific pass (full prompt and response detail):**
```bash
DAVE_LOG_LEVEL=DEBUG DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine
```

**Using Haiku for a cheaper test run:**
```bash
DAVE_CLAUDE_MODEL=claude-haiku-4-5-20251001 DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine
```

**Running Tier 2 tests:**
```bash
export ANTHROPIC_API_KEY=your_key_here
pytest --llm
```

**Running all tests including LLM-as-judge evaluation:**
```bash
pytest --llm-eval
```
