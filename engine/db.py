"""
engine/db.py — DAVE RPG Engine Database Layer

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

All database access lives here. No other module in the engine issues SQL
directly; they call methods on a Database instance instead. This keeps the
query logic in one place and makes it straightforward to audit, test, or
extend.

The underlying database is SQLite. Foreign key enforcement is enabled on every
connection. Row results are returned as plain dicts (via sqlite3.Row) so
callers don't need to know column positions.

Typical usage:

    from engine.db import Database

    db = Database("modules/i_am_a_cat/i_am_a_cat.db")
    player = db.get_player_character(game_id=1)
    db.update_internal_state(player["id"], "boredom", 0.65)
    db.close()

    # Or as a context manager:
    with Database("game.db") as db:
        game = db.get_game(game_id=1)
"""

import json
import logging
import random
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _format_game_time(minutes_past_midnight: int) -> str:
    """
    Convert a minutes-past-midnight value to a human-readable time string.

    Examples:
        180  → '3:00 AM'
        495  → '8:15 AM'
        720  → '12:00 PM'
        1350 → '10:30 PM'

    Handles values beyond 1439 (midnight) gracefully by applying modulo 1440,
    so sessions that run past midnight display correctly.
    """
    total = minutes_past_midnight % 1440
    hour_24 = total // 60
    minute = total % 60
    period = "AM" if hour_24 < 12 else "PM"
    hour_12 = hour_24 % 12 or 12  # converts 0 → 12, 13 → 1, etc.
    return f"{hour_12}:{minute:02d} {period}"


class Database:
    """
    Wrapper around a SQLite connection providing typed query and write methods
    for every operation the engine needs.

    All methods that return a single record return a dict or None.
    All methods that return multiple records return a list of dicts (possibly
    empty). Callers should always check for None / empty list before use.
    """

    def __init__(self, db_path: str | Path) -> None:
        """
        Open a connection to the SQLite database at db_path.

        Args:
            db_path: Path to the .db file. The file must already exist and
                     have the DAVE schema applied (schema.sql + migrations).
        """
        self._path = Path(db_path)
        if not self._path.exists():
            raise FileNotFoundError(
                f"Database file not found: {self._path}. "
                f"Create it by running schema.sql and seed.sql first."
            )
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row   # rows accessible as dicts
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")  # safe concurrent reads
        logger.debug("Opened database: %s", self._path)

    # -------------------------------------------------------------------------
    # Context manager support
    # -------------------------------------------------------------------------

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            logger.debug("Closed database: %s", self._path)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _row(self, sql: str, params: tuple = ()) -> dict | None:
        """Execute sql and return the first row as a dict, or None."""
        cursor = self._conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def _rows(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute sql and return all rows as a list of dicts."""
        cursor = self._conn.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a write statement and return the cursor."""
        cursor = self._conn.execute(sql, params)
        self._conn.commit()
        return cursor

    # -------------------------------------------------------------------------
    # Game record
    # -------------------------------------------------------------------------

    def get_game(self, game_id: int) -> dict | None:
        """
        Return the game record for game_id.

        The game record contains stable world parameters (genre, tone, speech
        filter, cultural norms, etc.) that are passed to every LLM call.
        JSON fields are parsed into Python objects before returning.
        """
        row = self._row("SELECT * FROM game WHERE id = ?", (game_id,))
        if row:
            row["speech_filter"] = json.loads(row["speech_filter"] or "{}")
            row["internal_state_display"] = json.loads(
                row["internal_state_display"] or "{}"
            )
            row["cultural_norms"] = json.loads(row["cultural_norms"] or "{}")
        return row

    # -------------------------------------------------------------------------
    # Character queries
    # -------------------------------------------------------------------------

    def get_character(self, character_id: int) -> dict | None:
        """
        Return a full character record by ID. JSON fields are parsed.
        Returns None if character_id does not exist.
        """
        row = self._row("SELECT * FROM character WHERE id = ?", (character_id,))
        if row:
            row["capability_beliefs"] = json.loads(row["capability_beliefs"] or "{}")
            row["context_beliefs"] = json.loads(row["context_beliefs"] or "{}")
        return row

    def get_player_character(self, game_id: int) -> dict | None:
        """
        Return the character with role='player' for the given game.
        There should be exactly one; returns None if none exists.
        """
        row = self._row(
            "SELECT * FROM character WHERE game_id = ? AND role = 'player'",
            (game_id,),
        )
        if row:
            row["capability_beliefs"] = json.loads(row["capability_beliefs"] or "{}")
            row["context_beliefs"] = json.loads(row["context_beliefs"] or "{}")
        return row

    def get_characters_at_location(
        self, location_id: int, exclude_character_id: int | None = None
    ) -> list[dict]:
        """
        Return all characters currently at location_id, optionally excluding
        a specific character (typically the player, to avoid self-reference
        in context packets).
        """
        if exclude_character_id is not None:
            rows = self._rows(
                """SELECT * FROM character
                   WHERE current_location_id = ? AND id != ?""",
                (location_id, exclude_character_id),
            )
        else:
            rows = self._rows(
                "SELECT * FROM character WHERE current_location_id = ?",
                (location_id,),
            )
        for row in rows:
            row["capability_beliefs"] = json.loads(row["capability_beliefs"] or "{}")
            row["context_beliefs"] = json.loads(row["context_beliefs"] or "{}")
        return rows

    # -------------------------------------------------------------------------
    # Goals, attitudes, skills, internal states
    # -------------------------------------------------------------------------

    def get_character_goals(
        self, character_id: int, include_hidden: bool = False
    ) -> list[dict]:
        """
        Return goal records for a character.

        Args:
            character_id: The character whose goals to fetch.
            include_hidden: If False (default), only surface goals are returned.
                            Pass True when assembling the adjudication packet,
                            where hidden motivation should be visible to the LLM
                            if access_hidden_motivation is set on the character.
        """
        if include_hidden:
            return self._rows(
                "SELECT * FROM character_goal WHERE character_id = ? ORDER BY priority DESC",
                (character_id,),
            )
        return self._rows(
            """SELECT * FROM character_goal
               WHERE character_id = ? AND goal_type = 'surface'
               ORDER BY priority DESC""",
            (character_id,),
        )

    def get_character_attitudes(
        self, character_id: int, include_hidden: bool = False
    ) -> list[dict]:
        """
        Return attitude records held by character_id toward other characters.

        Args:
            include_hidden: See get_character_goals(). Hidden attitudes are
                            included in adjudication packets only.
        """
        if include_hidden:
            return self._rows(
                "SELECT * FROM character_attitude WHERE character_id = ?",
                (character_id,),
            )
        return self._rows(
            """SELECT * FROM character_attitude
               WHERE character_id = ? AND attitude_type = 'surface'""",
            (character_id,),
        )

    def get_attitude_toward(
        self, character_id: int, target_id: int, attitude_type: str = "surface"
    ) -> float:
        """
        Return the attitude float that character_id holds toward target_id.
        Returns 0.0 (neutral) if no record exists.
        """
        row = self._row(
            """SELECT attitude FROM character_attitude
               WHERE character_id = ? AND target_id = ? AND attitude_type = ?""",
            (character_id, target_id, attitude_type),
        )
        return row["attitude"] if row else 0.0

    def get_character_skills(self, character_id: int) -> list[dict]:
        """Return all skill records for a character, ordered by skill level."""
        return self._rows(
            """SELECT * FROM character_skill
               WHERE character_id = ?
               ORDER BY skill_level DESC""",
            (character_id,),
        )

    def get_internal_states(self, character_id: int) -> list[dict]:
        """Return all internal state records for a character."""
        return self._rows(
            "SELECT * FROM internal_state WHERE character_id = ?",
            (character_id,),
        )

    def get_internal_state(self, character_id: int, state_name: str) -> dict | None:
        """Return a single named internal state record, or None."""
        return self._row(
            "SELECT * FROM internal_state WHERE character_id = ? AND state_name = ?",
            (character_id, state_name),
        )

    # -------------------------------------------------------------------------
    # Location queries
    # -------------------------------------------------------------------------

    def get_location(self, location_id: int) -> dict | None:
        """
        Return a location record. JSON fields (situation_flags) are parsed.
        """
        row = self._row("SELECT * FROM location WHERE id = ?", (location_id,))
        if row:
            row["situation_flags"] = json.loads(row["situation_flags"] or "[]")
        return row

    def get_all_locations(self) -> list[dict]:
        """
        Return a compact list of all locations in the database: id and name only.

        Used by Pass 1 to resolve player-supplied location names (e.g. "kitchen")
        to their database IDs so the engine can invoke multi-step pathfinding.
        Each module has its own database, so all rows belong to the current game.
        """
        return self._rows("SELECT id, name FROM location ORDER BY id")

    def get_location_details(
        self, location_id: int, max_results: int = 10
    ) -> list[dict]:
        """
        Return valid (is_valid=1) location_detail entries for a location,
        most recently generated first, capped at max_results.
        """
        return self._rows(
            """SELECT * FROM location_detail
               WHERE location_id = ? AND is_valid = 1
               ORDER BY generated_at DESC
               LIMIT ?""",
            (location_id, max_results),
        )

    # -------------------------------------------------------------------------
    # Location connection queries (v3+)
    # -------------------------------------------------------------------------

    def get_location_connections(self, location_id: int) -> list[dict]:
        """
        Return all passable connections for a location as a list of dicts.
        Each dict includes the neighbour's location_id and connection_type.

        Because the schema stores connections with a_id < b_id, we query both
        directions and return a unified list. The returned 'neighbour_id' field
        always refers to the other location (not location_id itself).

        Only currently passable connections (is_passable=1) are returned.
        Use is_location_connected() if you need to check a specific pair.
        """
        rows = self._rows(
            """SELECT
                   CASE
                       WHEN location_a_id = ? THEN location_b_id
                       ELSE location_a_id
                   END AS neighbour_id,
                   connection_type,
                   is_passable
               FROM location_connection
               WHERE (location_a_id = ? OR location_b_id = ?)
                 AND is_passable = 1""",
            (location_id, location_id, location_id),
        )
        return rows

    def is_location_connected(
        self, from_location_id: int, to_location_id: int
    ) -> bool:
        """
        Return True if there is a currently passable connection between the two
        locations (in either direction). Used to validate movement actions
        before applying them.
        """
        a, b = sorted([from_location_id, to_location_id])
        row = self._row(
            """SELECT 1 FROM location_connection
               WHERE location_a_id = ? AND location_b_id = ? AND is_passable = 1""",
            (a, b),
        )
        return row is not None

    def get_wandering_npcs(self, game_id: int) -> list[dict]:
        """
        Return all NPC characters in the game whose wander_probability > 0.

        These are candidates for autonomous background movement each turn.
        The wander_range JSON field is parsed into a Python list before returning.
        Only NPCs are returned (role != 'player').
        """
        rows = self._rows(
            """SELECT * FROM character
               WHERE game_id = ?
                 AND role != 'player'
                 AND wander_probability > 0.0""",
            (game_id,),
        )
        for row in rows:
            row["capability_beliefs"] = json.loads(row["capability_beliefs"] or "{}")
            row["context_beliefs"] = json.loads(row["context_beliefs"] or "{}")
            row["wander_range"] = json.loads(row["wander_range"] or "[]")
        return rows

    # -------------------------------------------------------------------------
    # Item queries
    # -------------------------------------------------------------------------

    def get_items_at_location(
        self, location_id: int, visible_only: bool = True, max_results: int = 12
    ) -> list[dict]:
        """
        Return items present at a location. By default returns only visible
        items (is_visible=1); pass visible_only=False to include hidden items
        (e.g. when the player is specifically searching for hidden items).
        """
        if visible_only:
            return self._rows(
                """SELECT * FROM item
                   WHERE location_id = ? AND is_visible = 1
                   ORDER BY id
                   LIMIT ?""",
                (location_id, max_results),
            )
        return self._rows(
            "SELECT * FROM item WHERE location_id = ? ORDER BY id LIMIT ?",
            (location_id, max_results),
        )

    def get_items_held_by(self, character_id: int) -> list[dict]:
        """Return all items currently held by a character."""
        return self._rows(
            "SELECT * FROM item WHERE held_by_character_id = ?",
            (character_id,),
        )

    # -------------------------------------------------------------------------
    # Interaction history
    # -------------------------------------------------------------------------

    def get_interaction_history(
        self, character_a_id: int, character_b_id: int
    ) -> dict | None:
        """
        Return the NPC-player history record for a pair of characters.
        By convention character_a_id < character_b_id; this method normalises
        the order automatically so callers don't need to remember the rule.
        """
        a, b = sorted([character_a_id, character_b_id])
        return self._row(
            """SELECT * FROM npc_player_history
               WHERE character_a_id = ? AND character_b_id = ?""",
            (a, b),
        )

    # -------------------------------------------------------------------------
    # Action log
    # -------------------------------------------------------------------------

    def get_recent_actions(self, game_id: int, limit: int = 5) -> list[dict]:
        """
        Return the most recent action_log entries for a game, newest first.
        action_json is parsed into a Python dict before returning.
        """
        rows = self._rows(
            """SELECT * FROM action_log
               WHERE game_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (game_id, limit),
        )
        for row in rows:
            row["action_json"] = json.loads(row["action_json"] or "{}")
        # Return in chronological order (oldest first) for context readability.
        return list(reversed(rows))

    # -------------------------------------------------------------------------
    # Write methods
    # -------------------------------------------------------------------------

    def update_internal_state(
        self, character_id: int, state_name: str, new_value: float
    ) -> None:
        """
        Set a named internal state to new_value for a character.
        new_value is clamped to [0.0, 1.0] before writing.

        If the state record does not yet exist, it is created with display_mode
        'prose' and no involuntary event settings.
        """
        new_value = max(0.0, min(1.0, new_value))
        self._execute(
            """INSERT INTO internal_state (character_id, state_name, value, updated_at)
               VALUES (?, ?, ?, datetime('now'))
               ON CONFLICT(character_id, state_name)
               DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (character_id, state_name, new_value),
        )
        logger.debug(
            "internal_state updated: char=%d %s=%.3f", character_id, state_name, new_value
        )

    def apply_internal_state_delta(
        self, character_id: int, state_name: str, delta: float
    ) -> float:
        """
        Add delta to the named internal state and return the resulting value.
        Clamps the result to [0.0, 1.0].
        """
        current = self.get_internal_state(character_id, state_name)
        current_value = current["value"] if current else 0.0
        new_value = max(0.0, min(1.0, current_value + delta))
        self.update_internal_state(character_id, state_name, new_value)
        return new_value

    def update_attitude(
        self,
        character_id: int,
        target_id: int,
        delta: float,
        attitude_type: str = "surface",
    ) -> float:
        """
        Apply a delta to an existing attitude and return the new value.
        Clamps to [-1.0, 1.0]. Creates the record at 0.0 if it doesn't exist.
        """
        current = self.get_attitude_toward(character_id, target_id, attitude_type)
        new_value = max(-1.0, min(1.0, current + delta))
        self._execute(
            """INSERT INTO character_attitude
                   (character_id, target_id, attitude, attitude_type, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'))
               ON CONFLICT(character_id, target_id, attitude_type)
               DO UPDATE SET attitude = excluded.attitude,
                             updated_at = excluded.updated_at""",
            (character_id, target_id, new_value, attitude_type),
        )
        logger.debug(
            "attitude updated: char=%d → target=%d %+.3f → %.3f",
            character_id, target_id, delta, new_value,
        )
        return new_value

    def update_character_location(
        self, character_id: int, new_location_id: int
    ) -> None:
        """Move a character to a new location and update the witness count."""
        old = self._row(
            "SELECT current_location_id FROM character WHERE id = ?",
            (character_id,),
        )
        self._execute(
            "UPDATE character SET current_location_id = ?, updated_at = datetime('now') WHERE id = ?",
            (new_location_id, character_id),
        )
        # Recalculate witness counts for old and new locations.
        if old and old["current_location_id"]:
            self._refresh_witness_count(old["current_location_id"])
        self._refresh_witness_count(new_location_id)

    def _refresh_witness_count(self, location_id: int) -> None:
        """Update location.witness_count to match current character occupancy."""
        row = self._row(
            "SELECT COUNT(*) AS n FROM character WHERE current_location_id = ?",
            (location_id,),
        )
        count = row["n"] if row else 0
        self._execute(
            "UPDATE location SET witness_count = ?, updated_at = datetime('now') WHERE id = ?",
            (count, location_id),
        )

    def update_character_emotional_state(
        self, character_id: int, emotional_state: str
    ) -> None:
        """Update a character's qualitative emotional state."""
        self._execute(
            "UPDATE character SET emotional_state = ?, updated_at = datetime('now') WHERE id = ?",
            (emotional_state, character_id),
        )

    def update_narrative_points(self, character_id: int, delta: int) -> int:
        """
        Apply a delta to a character's narrative points and return the new total.
        Points cannot go below zero.
        """
        row = self._row(
            "SELECT narrative_points FROM character WHERE id = ?", (character_id,)
        )
        current = row["narrative_points"] if row else 0
        new_total = max(0, current + delta)
        self._execute(
            "UPDATE character SET narrative_points = ?, updated_at = datetime('now') WHERE id = ?",
            (new_total, character_id),
        )
        return new_total

    def add_location_detail(
        self,
        location_id: int,
        detail: str,
        invalidation_condition: str | None = None,
    ) -> int:
        """
        Store a newly generated location detail (lazy world generation result).
        Returns the new row's id.
        """
        cursor = self._execute(
            """INSERT INTO location_detail
                   (location_id, detail, is_valid, invalidation_condition)
               VALUES (?, ?, 1, ?)""",
            (location_id, detail, invalidation_condition),
        )
        logger.debug(
            "location_detail added: loc=%d detail=%.60s…", location_id, detail
        )
        return cursor.lastrowid

    def invalidate_location_detail(self, detail_id: int) -> None:
        """Mark a location_detail as no longer valid (world state has changed)."""
        self._execute(
            """UPDATE location_detail
               SET is_valid = 0, invalidated_at = datetime('now')
               WHERE id = ?""",
            (detail_id,),
        )

    def write_action_log(
        self,
        game_id: int,
        character_id: int,
        action_json: dict,
        narrative_beat: str | None = None,
    ) -> int:
        """
        Append an entry to the action log. Returns the new row's id.
        Prunes old entries if the log exceeds ACTION_LOG_MAX_ROWS.
        """
        from engine import config  # local import avoids circular dependency

        cursor = self._execute(
            """INSERT INTO action_log
                   (game_id, character_id, action_json, narrative_beat)
               VALUES (?, ?, ?, ?)""",
            (game_id, character_id, json.dumps(action_json), narrative_beat),
        )
        new_id = cursor.lastrowid

        # Prune oldest rows if we have exceeded the configured maximum.
        row = self._row(
            "SELECT COUNT(*) AS n FROM action_log WHERE game_id = ?", (game_id,)
        )
        if row and row["n"] > config.ACTION_LOG_MAX_ROWS:
            self._execute(
                """DELETE FROM action_log WHERE game_id = ? AND id NOT IN (
                       SELECT id FROM action_log WHERE game_id = ?
                       ORDER BY created_at DESC LIMIT ?
                   )""",
                (game_id, game_id, config.ACTION_LOG_MAX_ROWS),
            )
        return new_id

    def update_interaction_history(
        self,
        character_a_id: int,
        character_b_id: int,
        new_summary: str | None = None,
        increment_count: bool = True,
    ) -> None:
        """
        Update the rolling interaction history between two characters.

        Args:
            character_a_id, character_b_id: The pair (order is normalised).
            new_summary: If provided, replaces the current summary and resets
                         the interaction counter (i.e. a fresh compression has
                         been generated).
            increment_count: If True, increments interactions_since_summary.
        """
        a, b = sorted([character_a_id, character_b_id])

        # Ensure the row exists.
        self._execute(
            """INSERT OR IGNORE INTO npc_player_history
                   (character_a_id, character_b_id, summary, interactions_since_summary)
               VALUES (?, ?, '', 0)""",
            (a, b),
        )

        if new_summary is not None:
            self._execute(
                """UPDATE npc_player_history
                   SET summary = ?, interactions_since_summary = 0,
                       updated_at = datetime('now')
                   WHERE character_a_id = ? AND character_b_id = ?""",
                (new_summary, a, b),
            )
        elif increment_count:
            self._execute(
                """UPDATE npc_player_history
                   SET interactions_since_summary = interactions_since_summary + 1,
                       updated_at = datetime('now')
                   WHERE character_a_id = ? AND character_b_id = ?""",
                (a, b),
            )

    def add_character_growth_event(
        self,
        character_id: int,
        description: str,
        changes: dict[str, Any],
    ) -> int:
        """
        Record a character growth event and return its id.
        changes should be a dict of field → {old, new} pairs.
        """
        cursor = self._execute(
            """INSERT INTO character_growth_event
                   (character_id, description, changes_json)
               VALUES (?, ?, ?)""",
            (character_id, description, json.dumps(changes)),
        )
        return cursor.lastrowid

    # -------------------------------------------------------------------------
    # Visited location tracking (v4+)
    # -------------------------------------------------------------------------

    def mark_location_visited(self, character_id: int, location_id: int) -> bool:
        """
        Record that character_id has visited location_id.

        Uses INSERT OR IGNORE so repeated calls are safe and cheap — no error
        or duplicate row if the location has already been visited.

        Returns True if this was the first visit (a new row was inserted),
        False if the location was already known to the character.
        """
        cursor = self._execute(
            """INSERT OR IGNORE INTO character_visited_location
                   (character_id, location_id)
               VALUES (?, ?)""",
            (character_id, location_id),
        )
        first_visit = cursor.rowcount > 0
        if first_visit:
            logger.debug(
                "First visit recorded: char=%d loc=%d", character_id, location_id
            )
        return first_visit

    def is_location_visited(self, character_id: int, location_id: int) -> bool:
        """
        Return True if character_id has previously visited location_id.
        Used to validate quick-move destinations.
        """
        row = self._row(
            """SELECT 1 FROM character_visited_location
               WHERE character_id = ? AND location_id = ?""",
            (character_id, location_id),
        )
        return row is not None

    def get_visited_locations(self, character_id: int) -> list[int]:
        """
        Return a list of location_ids that character_id has visited,
        ordered by first_visited_at ascending.
        """
        rows = self._rows(
            """SELECT location_id FROM character_visited_location
               WHERE character_id = ?
               ORDER BY first_visited_at ASC""",
            (character_id,),
        )
        return [r["location_id"] for r in rows]

    def find_path(
        self,
        from_location_id: int,
        to_location_id: int,
        max_steps: int = 20,
    ) -> list[int] | None:
        """
        Find the shortest path between two locations using BFS over passable
        connections.

        Returns a list of location_ids representing the steps to take, not
        including the starting location but including the destination. For
        example, find_path(1, 7) might return [5, 6, 7] meaning: go to Main
        Stairs, then Basement Main Room, then Basement Storage Room.

        Returns an empty list if from_location_id == to_location_id.
        Returns None if no passable path exists within max_steps steps.

        Args:
            from_location_id: The starting location.
            to_location_id:   The destination location.
            max_steps:        Maximum path length to search. Caps BFS depth
                              to bound search cost in large environments.
        """
        if from_location_id == to_location_id:
            return []

        # BFS: each queue entry is (current_location_id, path_so_far).
        # path_so_far does not include the starting location.
        queue: list[tuple[int, list[int]]] = [(from_location_id, [])]
        visited: set[int] = {from_location_id}

        while queue:
            current, path = queue.pop(0)

            if len(path) >= max_steps:
                # Depth cap reached for this branch; skip expansion.
                continue

            for conn in self.get_location_connections(current):
                neighbour = conn["neighbour_id"]
                next_path = path + [neighbour]

                if neighbour == to_location_id:
                    return next_path  # shortest path found

                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append((neighbour, next_path))

        return None  # no path found within max_steps

    # -------------------------------------------------------------------------
    # Game instance management (v5+)
    # -------------------------------------------------------------------------

    def get_active_instance(self, game_id: int) -> dict | None:
        """
        Return the active game_instance record for game_id — the most recent
        row with status 'ready' or 'active'.

        Returns None if no such instance exists, which means the module has not
        been seeded or the previous session reached a 'complete' state.
        """
        return self._row(
            """SELECT * FROM game_instance
               WHERE game_id = ?
                 AND status IN ('ready', 'active')
               ORDER BY id DESC
               LIMIT 1""",
            (game_id,),
        )

    def get_game_clock(self, instance_id: int) -> int:
        """
        Return the current in-game time in minutes past midnight for the given
        instance. Raises ValueError if the instance does not exist or the clock
        value is the unseeded sentinel (-1).
        """
        row = self._row(
            "SELECT current_time_minutes FROM game_instance WHERE id = ?",
            (instance_id,),
        )
        if row is None:
            raise ValueError(f"No game_instance with id={instance_id}")
        if row["current_time_minutes"] == -1:
            raise ValueError(
                f"game_instance {instance_id} has unseeded current_time_minutes (-1). "
                "Run seed_instance.sql before starting a session."
            )
        return row["current_time_minutes"]

    def advance_game_clock(self, instance_id: int, elapsed_minutes: int) -> int:
        """
        Add elapsed_minutes to the instance clock and return the new time.

        elapsed_minutes is expected to be a non-negative integer supplied by
        Pass 2's elapsed_minutes output field. Negative values are ignored with
        a warning to guard against malformed LLM output.

        The clock is not clamped — it can exceed 1439 (23:59) to represent
        sessions that run past midnight without requiring modular arithmetic
        on every caller. Time labels should use (current_time_minutes % 1440)
        when displaying hour/minute.
        """
        if elapsed_minutes < 0:
            logger.warning(
                "advance_game_clock called with negative elapsed_minutes=%d; ignoring",
                elapsed_minutes,
            )
            return self.get_game_clock(instance_id)

        self._execute(
            """UPDATE game_instance
               SET current_time_minutes = current_time_minutes + ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (elapsed_minutes, instance_id),
        )
        new_time = self.get_game_clock(instance_id)
        logger.debug(
            "game clock advanced: instance=%d +%d min → %d min (%s)",
            instance_id,
            elapsed_minutes,
            new_time,
            _format_game_time(new_time),
        )
        return new_time

    def tick_passive_states(self, game_id: int, elapsed_minutes: float) -> None:
        """
        Apply passive drift to all internal_state rows in the game that have a
        non-null passive_rate_per_minute.

        For each qualifying row:
            new_value = clamp(value + passive_rate_per_minute * elapsed_minutes,
                              0.0, 1.0)

        Called once per turn after the game clock has been advanced and Pass 2
        outcomes have been written, before Pass 3 runs.

        elapsed_minutes is a float here (the same value used for clock advance)
        to preserve sub-minute precision when rates are very small (e.g. 0.0003
        for hairball_pressure). The value field is clamped to [0.0, 1.0] by
        both the SQL CHECK constraint and the arithmetic below.
        """
        if elapsed_minutes <= 0:
            return

        # Fetch all states with a passive rate across all characters in this game.
        states = self._rows(
            """SELECT i.id, i.character_id, i.state_name, i.value,
                      i.passive_rate_per_minute
               FROM internal_state i
               JOIN character c ON c.id = i.character_id
               WHERE c.game_id = ?
                 AND i.passive_rate_per_minute IS NOT NULL""",
            (game_id,),
        )

        for state in states:
            new_value = state["value"] + state["passive_rate_per_minute"] * elapsed_minutes
            new_value = max(0.0, min(1.0, new_value))
            if abs(new_value - state["value"]) < 1e-9:
                continue  # no meaningful change; skip the write
            self._execute(
                """UPDATE internal_state
                   SET value = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (new_value, state["id"]),
            )
            logger.debug(
                "passive tick: char=%d %s %.4f → %.4f (rate=%+.5f × %.1f min)",
                state["character_id"],
                state["state_name"],
                state["value"],
                new_value,
                state["passive_rate_per_minute"],
                elapsed_minutes,
            )

    def set_instance_status(self, instance_id: int, status: str) -> None:
        """
        Update the lifecycle status of a game_instance.

        Valid transitions: pending → ready → active → complete.
        The CHECK constraint on the status column enforces valid values at the
        database level; this method provides a named interface so callers don't
        scatter raw SQL updates.
        """
        self._execute(
            """UPDATE game_instance
               SET status = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (status, instance_id),
        )
        logger.debug("instance status: id=%d → %s", instance_id, status)

    # -------------------------------------------------------------------------
    # Involuntary event support
    # -------------------------------------------------------------------------

    def get_involuntary_states(self, game_id: int) -> list[dict]:
        """
        Return all internal_state records across all characters in the game
        where is_involuntary = 1. Called once per turn to check whether any
        involuntary events should fire.
        """
        return self._rows(
            """SELECT i.*, c.name AS character_name, c.species AS character_species
               FROM internal_state i
               JOIN character c ON c.id = i.character_id
               WHERE c.game_id = ? AND i.is_involuntary = 1""",
            (game_id,),
        )

    def roll_involuntary_event(self, state: dict) -> bool:
        """
        Determine whether an involuntary event fires this turn for the given
        internal_state record.

        For 'probabilistic' triggers:
            probability = min(value * trigger_param, INVOLUNTARY_MAX_PROB)
        For 'threshold' triggers:
            fires if value >= trigger_param

        Returns True if the event should fire, False otherwise.
        """
        from engine import config  # local import

        trigger_type = state.get("involuntary_trigger_type")
        trigger_param = state.get("involuntary_trigger_param") or 0.0
        value = state.get("value", 0.0)

        if trigger_type == "probabilistic":
            probability = min(value * trigger_param, config.INVOLUNTARY_MAX_PROB)
            fired = random.random() < probability
            if fired:
                logger.info(
                    "Involuntary event fired: char=%d state=%s value=%.3f prob=%.3f",
                    state["character_id"],
                    state["state_name"],
                    value,
                    probability,
                )
            return fired

        if trigger_type == "threshold":
            return value >= trigger_param

        return False
