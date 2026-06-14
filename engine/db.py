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

    def get_all_npcs(self) -> list[dict]:
        """
        Return a compact list of all non-player characters: id, name, species.

        Used by Pass 1 to resolve player-supplied character references (e.g.
        "spook", "the cat", "mama") to their database IDs. Species is included
        so the LLM can disambiguate references by type ("the cat" vs. "the bird")
        when the player does not use a character's name directly.

        The player character (role='player') is excluded — Pass 1 needs to
        resolve NPC targets only; the player is always the actor, not the target.
        Each module has its own database, so all rows belong to the current game.
        """
        return self._rows(
            """SELECT id, name, species
               FROM character
               WHERE role != 'player'
               ORDER BY id"""
        )

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
                   is_passable,
                   passage_note
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
    # Item queries (v9+)
    # -------------------------------------------------------------------------

    def get_items_at_location(
        self, location_id: int, max_results: int = 12, visible_only: bool = False
    ) -> list[dict]:
        """
        Return items whose loc_id matches location_id (v10 schema).

        Items held by characters (char_id set) or inside containers (item_id set)
        are not returned — this query is scoped to location-resident items only.
        Properties JSON is parsed before returning.

        Args:
            location_id:  The location to query.
            max_results:  Cap on rows returned (guards against very cluttered spaces).
            visible_only: When True, exclude unconfirmed items (is_confirmed = 0).
                          Used by path-interruption checks so player-declared but
                          not-yet-adjudicated items don't block movement.
        """
        confirmed_clause = " AND is_confirmed = 1" if visible_only else ""
        rows = self._rows(
            f"""SELECT * FROM item
               WHERE loc_id = ?{confirmed_clause}
               ORDER BY id
               LIMIT ?""",
            (location_id, max_results),
        )
        for row in rows:
            row["properties"] = json.loads(row.get("properties") or "{}")
        return rows

    def get_character_inventory(self, character_id: int) -> list[dict]:
        """
        Return all items currently held by a character (v10 schema).

        In v10 the slot field lives directly on the item row (char_id FK replaces
        the old character_item join table). Each returned dict is a full item row
        including slot and location_description. Properties JSON is parsed before
        returning.

        Args:
            character_id: The character whose inventory to fetch.
        """
        rows = self._rows(
            """SELECT * FROM item
               WHERE char_id = ?
               ORDER BY id""",
            (character_id,),
        )
        for row in rows:
            row["properties"] = json.loads(row.get("properties") or "{}")
        return rows

    def create_item(
        self,
        game_id: int,
        name: str,
        description: str | None = None,
        properties: dict | None = None,
        is_confirmed: int = 1,
        loc_id: int | None = None,
        char_id: int | None = None,
        item_id: int | None = None,
        slot: str | None = None,
        location_description: str | None = None,
    ) -> int:
        """
        Insert a new item record and return its id (v10 schema).

        Exactly one of loc_id, char_id, or item_id must be provided — the schema
        CHECK constraint enforces this at the database layer. Called by the engine
        when Pass 2 emits an item_instantiations entry. Seeded items are inserted
        directly by seed.sql at game build time and do not go through this method.

        Args:
            game_id:              The game this item belongs to.
            name:                 Short canonical name (e.g. 'sencha canister').
            description:          Prose description, or None if not yet known.
            properties:           Dict of module-specific attributes (serialised
                                  to JSON). Defaults to {} if None.
            is_confirmed:         1 = real item (default); 0 = player-claimed
                                  placeholder not yet adjudicated.
            loc_id:               Location id if item is at a location.
            char_id:              Character id if item is held by a character.
            item_id:              Container item id if item is inside another item.
            slot:                 How the character carries/wears the item — only
                                  meaningful when char_id is set.
            location_description: Natural-language description of where within the
                                  location/character/container the item sits.

        Returns:
            The new item's id.
        """
        props_json = json.dumps(properties or {})
        cursor = self._execute(
            """INSERT INTO item
                   (game_id, name, description, properties, is_confirmed,
                    loc_id, char_id, item_id,
                    slot, location_description,
                    created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (game_id, name, description, props_json, is_confirmed,
             loc_id, char_id, item_id,
             slot, location_description),
        )
        new_id = cursor.lastrowid
        logger.info(
            "Item created: id=%d name=%r game=%d confirmed=%d loc=%s char=%s container=%s",
            new_id, name, game_id, is_confirmed, loc_id, char_id, item_id,
        )
        return new_id

    def transfer_item_to_character(
        self,
        item_id: int,
        character_id: int,
        slot: str = "carried",
        location_description: str | None = None,
    ) -> None:
        """
        Move an item to a character's inventory (v10 schema).

        Sets char_id and clears loc_id and the container item_id in a single
        UPDATE. The slot field is updated in the same statement. The schema CHECK
        constraint guarantees exactly one FK is non-null after the update.

        Args:
            item_id:              The item to transfer.
            character_id:         The character who will hold the item.
            slot:                 How the character carries it (e.g. 'in_pack',
                                  'worn', 'right_hand'). Descriptive only — no
                                  uniqueness enforced at the schema layer.
            location_description: Optional natural-language description of where
                                  on the character the item is positioned.
        """
        self._execute(
            """UPDATE item
               SET char_id = ?, loc_id = NULL, item_id = NULL,
                   slot = ?, location_description = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (character_id, slot, location_description, item_id),
        )
        logger.info(
            "Item %d transferred to char=%d slot=%s", item_id, character_id, slot
        )

    def transfer_item_to_location(
        self,
        item_id: int,
        location_id: int,
        location_description: str | None = None,
        is_confirmed: int | None = None,
    ) -> None:
        """
        Move an item to a location (v10 schema).

        Sets loc_id and clears char_id and container item_id in a single UPDATE.
        When the player deliberately drops an item, pass is_confirmed=1 to mark
        the item as intentionally placed and known to be there.

        Args:
            item_id:              The item to place.
            location_id:          The destination location.
            location_description: Natural-language description of where within
                                  the location the item sits.
            is_confirmed:         If provided, overrides the item's is_confirmed
                                  flag (pass 1 when player drops deliberately).
        """
        confirmed_clause = ", is_confirmed = ?" if is_confirmed is not None else ""
        params: tuple = (
            (location_id, location_description, is_confirmed, item_id)
            if is_confirmed is not None
            else (location_id, location_description, item_id)
        )
        self._execute(
            f"""UPDATE item
               SET loc_id = ?, char_id = NULL, item_id = NULL,
                   slot = NULL, location_description = ?{confirmed_clause},
                   updated_at = datetime('now')
               WHERE id = ?""",
            params,
        )
        logger.info("Item %d transferred to location=%d", item_id, location_id)

    def get_items_in_container(self, container_item_id: int) -> list[dict]:
        """
        Return items whose item_id matches container_item_id (v10 schema).

        Used to populate the `contents` field in location context packets so
        Pass 2 can reference item IDs when issuing item_transfers out of a
        container (e.g. rolls inside a tray, books on a shelf).
        Properties JSON is parsed before returning.

        Args:
            container_item_id: The id of the container item.
        """
        rows = self._rows(
            "SELECT * FROM item WHERE item_id = ? ORDER BY id",
            (container_item_id,),
        )
        for row in rows:
            row["properties"] = json.loads(row.get("properties") or "{}")
        return rows

    def transfer_item_to_container(
        self,
        item_id: int,
        container_item_id: int,
        location_description: str | None = None,
    ) -> None:
        """
        Move an item inside a container item (v10 schema).

        Sets the item_id FK (pointing to the container) and clears loc_id and
        char_id. Container hierarchy is resolved at query time via recursive CTE;
        moving a container does not cascade-update its contents.

        Args:
            item_id:              The item to place inside the container.
            container_item_id:    The item that acts as the container.
            location_description: Natural-language description of where within
                                  the container the item is positioned.
        """
        self._execute(
            """UPDATE item
               SET item_id = ?, loc_id = NULL, char_id = NULL,
                   slot = NULL, location_description = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (container_item_id, location_description, item_id),
        )
        logger.info(
            "Item %d transferred into container item=%d", item_id, container_item_id
        )

    def update_player_character(
        self,
        character_id: int,
        description: str | None = None,
        gender: str | None = None,
        pronouns: str | None = None,
    ) -> None:
        """
        Update identity fields on the player character record.

        Called by the engine when Pass 2 returns a player_character_update entry
        — most commonly during self-definition at the start of a 'define'-mode
        module, but usable in any module where the player corrects or elaborates
        their character's appearance. Only non-None arguments are written; passing
        None for a field leaves that field unchanged.

        Args:
            character_id: The player character's id.
            description:  Prose description (as would appear in a mirror).
            gender:       Gender label string, or None to leave unchanged.
            pronouns:     JSON-serialisable pronoun list, or a JSON string, or
                          None to leave unchanged. The engine passes either a
                          Python list (from Pass 2 JSON) or an already-serialised
                          string; this method normalises both.
        """
        updates: list[str] = []
        params: list[Any] = []

        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if gender is not None:
            updates.append("gender = ?")
            params.append(gender)
        if pronouns is not None:
            # Normalise: accept a Python list or a JSON string.
            if isinstance(pronouns, list):
                pronouns = json.dumps(pronouns)
            updates.append("pronouns = ?")
            params.append(pronouns)

        if not updates:
            logger.debug("update_player_character: no fields to update for char=%d", character_id)
            return

        updates.append("updated_at = datetime('now')")
        params.append(character_id)
        self._execute(
            f"UPDATE character SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        logger.info(
            "Player character updated: char=%d fields=%s",
            character_id,
            [u.split(' =')[0] for u in updates[:-1]],
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

    # -------------------------------------------------------------------------
    # Faction reputation (v7+)
    # -------------------------------------------------------------------------

    def get_character_faction_reputations(self, character_id: int) -> list[dict]:
        """
        Return all faction reputation records for a character, joined with the
        faction name and description so the context packet has everything it
        needs without a separate faction lookup.

        Returns a list of dicts with keys:
            faction_id, faction_name, faction_description, reputation, notes

        An empty list is returned for characters with no faction records (e.g.
        NPCs in modules that don't use factions, or the I Am a Cat module).
        """
        return self._rows(
            """SELECT
                   cfr.faction_id,
                   f.name    AS faction_name,
                   f.description AS faction_description,
                   cfr.reputation,
                   cfr.notes
               FROM character_faction_reputation cfr
               JOIN faction f ON f.id = cfr.faction_id
               WHERE cfr.character_id = ?
               ORDER BY f.name""",
            (character_id,),
        )

    def update_faction_reputation(
        self,
        character_id: int,
        faction_id: int,
        delta: float,
        reason: str | None = None,
    ) -> float:
        """
        Apply a delta to a character's standing with a faction and return the
        new value. Clamps to [0.0, 1.0].

        If no reputation record exists for this (character, faction) pair, the
        record is created at 0.5 (neutral) before the delta is applied.

        Args:
            character_id: The character whose reputation changes.
            faction_id:   The faction whose opinion of the character changes.
            delta:        Signed float to add. Typical range: ±0.05 to ±0.15.
            reason:       Optional human-readable note written to the notes field.
                          Pass 2 supplies this from the outcome's reason string.

        Returns:
            The new reputation float after clamping.
        """
        # Ensure a record exists (default 0.5) before reading current value.
        self._execute(
            """INSERT OR IGNORE INTO character_faction_reputation
                   (character_id, faction_id, reputation)
               VALUES (?, ?, 0.5)""",
            (character_id, faction_id),
        )

        row = self._row(
            """SELECT reputation FROM character_faction_reputation
               WHERE character_id = ? AND faction_id = ?""",
            (character_id, faction_id),
        )
        current = row["reputation"] if row else 0.5
        new_value = max(0.0, min(1.0, current + delta))

        self._execute(
            """UPDATE character_faction_reputation
               SET reputation = ?,
                   notes      = COALESCE(?, notes),
                   updated_at = datetime('now')
               WHERE character_id = ? AND faction_id = ?""",
            (new_value, reason, character_id, faction_id),
        )
        logger.debug(
            "faction reputation: char=%d faction=%d %+.3f → %.3f",
            character_id, faction_id, delta, new_value,
        )
        return new_value

    def get_or_create_faction(
        self, game_id: int, name: str, description: str = ""
    ) -> dict:
        """
        Return the faction record matching (game_id, name), creating it if it
        does not yet exist.

        This is used when Pass 2 issues a create_faction outcome during play
        (e.g. a new alliance forms, a family is founded). The schema requires
        no modification for this use case — factions are data, not schema.

        Args:
            game_id:     The module's game id (faction names are scoped per game).
            name:        Snake_case slug, e.g. 'wickham_militia_circle'.
            description: LLM-facing description of the faction's values and
                         judgment criteria. May be empty for dynamically created
                         factions; Pass 2 should supply it from the outcome JSON.

        Returns:
            The faction row dict (id, game_id, name, description, created_at).
        """
        existing = self._row(
            "SELECT * FROM faction WHERE game_id = ? AND name = ?",
            (game_id, name),
        )
        if existing:
            return existing

        cursor = self._execute(
            "INSERT INTO faction (game_id, name, description) VALUES (?, ?, ?)",
            (game_id, name, description),
        )
        logger.info(
            "Faction created: game=%d name=%s id=%d", game_id, name, cursor.lastrowid
        )
        return self._row("SELECT * FROM faction WHERE id = ?", (cursor.lastrowid,))

    def update_character_pending_intent(
        self, character_id: int, intent_text: str | None
    ) -> None:
        """
        Set or clear the pending_intent working-memory slot on a character.

        pending_intent is a short natural-language description of a social
        obligation the character has not yet fulfilled (e.g. 'owes Bingley a
        response to his dinner invitation'). When non-null it suppresses the
        NPC's autonomous wander roll — convention forbids simply wandering off
        mid-obligation.

        Pass None to clear the intent (obligation fulfilled or abandoned).

        Args:
            character_id: The NPC whose pending_intent to update.
            intent_text:  The new intent string, or None to clear.
        """
        self._execute(
            """UPDATE character
               SET pending_intent = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (intent_text, character_id),
        )
        logger.debug(
            "pending_intent updated: char=%d → %r",
            character_id,
            intent_text[:60] if intent_text else None,
        )

    # =========================================================================
    # TIMED ACTIVITY SYSTEM (added v8)
    # current_activity tracks what an NPC is currently doing with an expected
    # duration and confidence estimate. Distinct from pending_intent (a
    # commitment slot) — activity persists through commitment fulfillment and
    # suppresses the wander roll for as long as it is active.
    # =========================================================================

    def set_character_activity(
        self,
        character_id: int,
        activity: str,
        started_at: int,
        duration_minutes: int | None,
        confidence: float | None,
        renewable: int,
    ) -> None:
        """
        Set or replace the current_activity on a character.

        Called by the engine when applying an 'activity_updates' entry from
        Pass 2 outcome JSON. The engine supplies started_at from the current
        game clock — Pass 2 never sets the start timestamp directly.

        Args:
            character_id:     The character whose activity to set.
            activity:         Natural language description of the activity.
            started_at:       Game clock minute when the activity begins
                              (current_time_minutes from game_instance at
                              the moment of apply).
            duration_minutes: Estimated duration in game-clock minutes, or
                              None for open-ended activities (no auto-expiry).
            confidence:       Confidence in the duration estimate (0.0–1.0),
                              or None when duration_minutes is None.
            renewable:        1 = persists past estimated expiry until Pass 2
                              clears it explicitly. 0 = engine may auto-clear
                              on high-confidence expiry.
        """
        self._execute(
            """UPDATE character
               SET current_activity             = ?,
                   activity_started_at          = ?,
                   activity_estimated_duration  = ?,
                   activity_duration_confidence = ?,
                   activity_renewable           = ?,
                   updated_at                   = datetime('now')
               WHERE id = ?""",
            (activity, started_at, duration_minutes, confidence, renewable, character_id),
        )
        logger.info(
            "activity set: char=%d activity=%r started_at=%d duration=%s confidence=%s renewable=%d",
            character_id,
            activity[:60],
            started_at,
            duration_minutes,
            confidence,
            renewable,
        )

    def clear_character_activity(self, character_id: int) -> None:
        """
        Clear the current_activity on a character, setting all five activity
        fields to NULL / default.

        Called by the engine in two cases:
          1. Mechanical expiry: high-confidence, non-renewable activity whose
             estimated duration has elapsed (engine-driven).
          2. Explicit Pass 2 clear: activity_updates entry with activity=null
             in the outcome JSON (LLM-driven).

        Args:
            character_id: The character whose activity to clear.
        """
        self._execute(
            """UPDATE character
               SET current_activity             = NULL,
                   activity_started_at          = NULL,
                   activity_estimated_duration  = NULL,
                   activity_duration_confidence = NULL,
                   activity_renewable           = 0,
                   updated_at                   = datetime('now')
               WHERE id = ?""",
            (character_id,),
        )
        logger.debug("activity cleared: char=%d", character_id)

    def get_characters_with_expired_activities(
        self, game_id: int, current_time_minutes: int, confidence_threshold: float
    ) -> list[dict]:
        """
        Return all characters in this game whose current_activity has
        mechanically expired and is eligible for auto-clearing.

        Eligibility criteria (all must be true):
          - current_activity IS NOT NULL (activity is set)
          - activity_estimated_duration IS NOT NULL (not open-ended)
          - activity_renewable = 0 (not marked as persisting past expiry)
          - activity_duration_confidence >= confidence_threshold (high confidence)
          - activity_started_at + activity_estimated_duration <= current_time_minutes
            (estimated end time has passed)

        The engine calls this once per turn, before processing player input,
        and calls clear_character_activity() on each result.

        Args:
            game_id:              The game instance to check.
            current_time_minutes: Current game clock value (from game_instance).
            confidence_threshold: Minimum confidence for auto-clear eligibility
                                  (typically config.ACTIVITY_AUTO_CLEAR_CONFIDENCE).

        Returns:
            List of character row dicts for characters with expired activities.
            Each dict includes at minimum: id, name, current_activity,
            activity_started_at, activity_estimated_duration,
            activity_duration_confidence, activity_renewable.
        """
        return self._rows(
            """SELECT *
               FROM character
               WHERE game_id = ?
                 AND current_activity IS NOT NULL
                 AND activity_estimated_duration IS NOT NULL
                 AND activity_renewable = 0
                 AND activity_duration_confidence >= ?
                 AND (activity_started_at + activity_estimated_duration)
                         <= ?""",
            (game_id, confidence_threshold, current_time_minutes),
        )

    # =========================================================================
    # LAZY NPC CREATION (added session 14)
    # Creates a new background NPC at runtime from Pass 2-supplied skeleton data.
    # Used when the player references a character not in the cast but whose
    # existence is plausible (family member, neighbour, etc.).
    # =========================================================================

    def create_character(
        self,
        game_id: int,
        name: str,
        description: str | None = None,
        emotional_state: str = "neutral",
        current_location_id: int | None = None,
        gender: str | None = None,
        pronouns: str | None = None,
        role: str = "npc_background",
        species: str = "human",
        ocean_openness: float | None = None,
        ocean_conscientiousness: float | None = None,
        ocean_extraversion: float | None = None,
        ocean_agreeableness: float | None = None,
        ocean_neuroticism: float | None = None,
    ) -> dict:
        """
        Insert a new NPC record with skeleton data and return the created row.

        Called by the engine when Pass 2 emits a new_characters entry — i.e.
        when the player references a plausible character not yet in the DB
        (e.g. 'Maria Lucas', whose surname matches a present character and who
        would naturally be at the event). Once created, the character is
        canonical and will appear in context packets from the next turn onward.

        Required by caller:
            game_id: The game this character belongs to.
            name:    The character's full name as Pass 2 supplied it.

        Optional — supply what Pass 2 generated; everything else gets a
        sensible default that the engine or future Pass 2 calls can refine:
            description:        Brief prose description for the context packet.
            emotional_state:    Starting emotional state (default 'neutral').
            current_location_id: Where the character is (None = unplaced).
            gender:             Gender label (None = LLM infers).
            pronouns:           JSON array of pronoun forms (None = LLM infers).
            role:               Character role (default 'npc_background').
            species:            Species (default 'human').
            ocean_*:            OCEAN trait floats (None = not yet assessed;
                                Pass 2 will infer from behaviour until set).

        Returns:
            The newly created character row as a dict.
        """
        cursor = self._execute(
            """INSERT INTO character (
                   game_id, name, role, species, description, emotional_state,
                   current_location_id, gender, pronouns,
                   ocean_openness, ocean_conscientiousness, ocean_extraversion,
                   ocean_agreeableness, ocean_neuroticism,
                   wander_probability, narrative_points,
                   created_at, updated_at
               ) VALUES (
                   ?, ?, ?, ?, ?, ?,
                   ?, ?, ?,
                   ?, ?, ?, ?, ?,
                   0.0, 0,
                   datetime('now'), datetime('now')
               )""",
            (
                game_id, name, role, species, description, emotional_state,
                current_location_id, gender, pronouns,
                ocean_openness, ocean_conscientiousness, ocean_extraversion,
                ocean_agreeableness, ocean_neuroticism,
            ),
        )
        new_id = cursor.lastrowid
        logger.info(
            "Lazy NPC created: id=%d name=%r location=%s",
            new_id, name, current_location_id,
        )
        return self._row("SELECT * FROM character WHERE id = ?", (new_id,))
