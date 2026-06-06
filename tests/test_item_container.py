"""
tests/test_item_container.py — Item Container Hierarchy Tests

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Contains two test classes:

TestSurfaceVisibility (Tier 1, no LLM required)
  Verifies that the recursive surface walk in _build_location_context correctly
  exposes items on surfaces to Pass 2. Three cases:
    - Kitchen: tray (surface) has 12 rolls visible in context
    - Common Room: plate on low table, 4 rolls on plate → nested visibility
    - Closed container: contents NOT shown (container: true)
  Runs in the default suite (no --llm flag needed).

TestItemContainerHierarchy (Tier 2, requires --llm)
  Tests the v10 item container hierarchy through a four-turn scenario:
    1. Player takes four rolls from the tray and places them on the plate.
    2. Player picks up the plate.
    3. Player carries the plate to the Common Room.
    4. Player sets the plate on the low table by the fire.
  Each turn checks the relevant DB state (item.loc_id, item.char_id, item.item_id).

Seeded item structure (Kitchen, location 2):
  kitchen worktable (loc_id=2, surface=true)
  tray of hot rolls (loc_id=2, surface=true)
    └── hot roll × 12 (item_id=tray)
  plate (loc_id=2, surface=true)

Seeded item structure (Common Room, location 1):
  chair by the fire (left)  (loc_id=1)
  chair by the fire (right) (loc_id=1)
  chair near the door       (loc_id=1)
  low table                 (loc_id=1, surface=true)

The player character is placed directly in the kitchen (location 2) for the
LLM tests — the entrance sequence is not repeated.
"""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from engine.context import _build_location_context
from engine.db import Database
from engine.engine import GameEngine

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_SCHEMA_SQL = _REPO_ROOT / "schema" / "schema.sql"
_HOSTEL_SEED = _REPO_ROOT / "modules" / "hidden_hostel" / "seed.sql"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def fresh_db():
    """
    Build a Hidden Hostel database from schema + seed and yield a Database
    instance. Function-scoped so each test gets a clean, unmodified DB.
    Used by the non-LLM surface visibility tests.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA_SQL.read_text(encoding="utf-8"))
        conn.executescript(_HOSTEL_SEED.read_text(encoding="utf-8"))
        conn.close()
        db = Database(path)
        yield db
        db.close()
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


@pytest.fixture(scope="module")
def item_db():
    """
    Build a Hidden Hostel database from schema + seed, place the player
    directly in the kitchen, and yield a Database instance.

    Teardown: closes the connection and deletes the temp file.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA_SQL.read_text(encoding="utf-8"))
        conn.executescript(_HOSTEL_SEED.read_text(encoding="utf-8"))

        # Place the player in the kitchen (location 2) directly.
        # Set a placeholder description so the engine doesn't enter
        # self-definition mode on the first turn.
        conn.execute(
            """UPDATE character
               SET current_location_id = 2,
                   description = 'A traveller, weary but curious.',
                   updated_at = datetime('now')
               WHERE game_id = 1 AND role = 'player'"""
        )
        # Mark the Kitchen as visited so multi-hop routing is available.
        conn.execute(
            "INSERT OR IGNORE INTO character_visited_location (character_id, location_id) "
            "VALUES (1, 2)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO character_visited_location (character_id, location_id) "
            "VALUES (1, 1)"
        )
        conn.commit()
        conn.close()

        db = Database(path)
        yield db
        db.close()
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


@pytest.fixture(scope="module")
def item_engine(item_db):
    """GameEngine against the item test DB. Module-scoped; state accumulates."""
    return GameEngine(db=item_db, game_id=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def take_turn(engine: GameEngine, player_input: str) -> str:
    """Run one complete turn; returns the prose output."""
    engine._check_activity_expiry()
    engine._check_npc_wandering()
    engine._player = engine.db.get_player_character(engine.game_id)
    return engine._process_turn(player_input, involuntary_fired=[])


def item_by_name(db: Database, name: str) -> dict | None:
    """Return the first item matching name for game_id=1, or None."""
    return db._row("SELECT * FROM item WHERE name = ? AND game_id = 1", (name,))


def rolls_in_tray(db: Database, tray_id: int) -> int:
    """Count rolls currently inside the tray."""
    row = db._row(
        "SELECT COUNT(*) AS n FROM item WHERE item_id = ? AND name = 'hot roll'",
        (tray_id,),
    )
    return row["n"] if row else 0


def rolls_on_char(db: Database, char_id: int) -> list[dict]:
    """Return roll items currently held by a character."""
    return db._rows(
        "SELECT * FROM item WHERE char_id = ? AND name = 'hot roll'",
        (char_id,),
    )


# =============================================================================
# Tests
# =============================================================================

# =============================================================================
# Tier 1: Surface visibility tests (no LLM required)
# =============================================================================

class TestSurfaceVisibility:
    """
    Non-LLM tests for the recursive surface walk in _build_location_context.

    These verify that Pass 2 receives the correct item hierarchy in its context
    packet — specifically that items on surfaces are visible, items nested on
    surfaces-on-surfaces are visible recursively, and closed container contents
    are NOT visible. Runs in the default suite without --llm.
    """

    def test_kitchen_tray_contents_visible(self, fresh_db: Database):
        """
        In the seeded kitchen (location 2), the tray of hot rolls is a surface
        item at loc_id=2. Its 12 roll contents (item_id=tray) must appear in
        the context packet so Pass 2 knows the roll item IDs.
        """
        ctx = _build_location_context(fresh_db, location_id=2)
        items_by_name = {i["name"]: i for i in ctx["items"]}

        assert "tray of hot rolls" in items_by_name, (
            "Tray of hot rolls should appear as a kitchen location item"
        )
        tray_summary = items_by_name["tray of hot rolls"]
        assert "contents" in tray_summary, (
            "Tray (surface: true) should have a contents field in the context"
        )
        assert len(tray_summary["contents"]) == 12, (
            f"Tray should show all 12 rolls; got {len(tray_summary['contents'])}"
        )
        # Each roll should carry its item id so Pass 2 can reference it
        roll_ids = {c["id"] for c in tray_summary["contents"]}
        assert len(roll_ids) == 12, "All 12 roll ids should be distinct"

    def test_kitchen_plate_visible_with_empty_contents(self, fresh_db: Database):
        """
        The plate is a surface item at loc_id=2 with no items on it initially.
        It should appear in the context with an empty contents list.
        """
        ctx = _build_location_context(fresh_db, location_id=2)
        items_by_name = {i["name"]: i for i in ctx["items"]}

        assert "plate" in items_by_name, "Plate should appear as a kitchen location item"
        plate_summary = items_by_name["plate"]
        assert "contents" in plate_summary, "Plate (surface: true) should have contents field"
        assert plate_summary["contents"] == [], (
            "Plate should have empty contents initially"
        )

    def test_closed_container_contents_not_visible(self, fresh_db: Database):
        """
        The sencha canister (container: true) is in the player's pack (char_id=1),
        but even if a closed container is at a location its contents should not
        appear. Add a test item inside the canister and verify it is hidden.
        """
        # Find the canister and place it at a location so it shows in context
        canister = fresh_db._row(
            "SELECT id FROM item WHERE name = 'sencha canister' AND game_id = 1"
        )
        # Move canister to kitchen (loc_id=2) temporarily
        fresh_db._execute(
            "UPDATE item SET loc_id = 2, char_id = NULL WHERE id = ?",
            (canister["id"],),
        )
        # Insert a test item inside the canister
        fresh_db._execute(
            """INSERT INTO item (game_id, name, description, properties, item_id)
               VALUES (1, 'hidden tea packet', 'A small paper packet of tea.', '{}', ?)""",
            (canister["id"],),
        )

        ctx = _build_location_context(fresh_db, location_id=2)
        items_by_name = {i["name"]: i for i in ctx["items"]}

        assert "sencha canister" in items_by_name, (
            "Canister should appear as a kitchen item when moved there"
        )
        canister_summary = items_by_name["sencha canister"]
        assert "contents" not in canister_summary, (
            "Closed container (container: true) should NOT expose contents in context"
        )

    def test_recursive_surface_nesting(self, fresh_db: Database):
        """
        Simulates the end state of the LLM scenario: plate on the low table,
        4 rolls on the plate. The Common Room context should expose the full
        hierarchy: low_table → plate → [roll × 4].

        This verifies depth-2 recursion through surfaces.
        """
        plate = fresh_db._row("SELECT id FROM item WHERE name = 'plate' AND game_id = 1")
        low_table = fresh_db._row("SELECT id FROM item WHERE name = 'low table' AND game_id = 1")
        tray = fresh_db._row("SELECT id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1")

        # Move plate onto the low table
        fresh_db._execute(
            "UPDATE item SET item_id = ?, loc_id = NULL, char_id = NULL WHERE id = ?",
            (low_table["id"], plate["id"]),
        )
        # Move 4 rolls from tray to plate
        rolls = fresh_db._rows(
            "SELECT id FROM item WHERE item_id = ? AND name = 'hot roll' LIMIT 4",
            (tray["id"],),
        )
        for roll in rolls:
            fresh_db._execute(
                "UPDATE item SET item_id = ? WHERE id = ?",
                (plate["id"], roll["id"]),
            )

        ctx = _build_location_context(fresh_db, location_id=1)
        items_by_name = {i["name"]: i for i in ctx["items"]}

        assert "low table" in items_by_name, "Low table should appear in Common Room items"
        table_summary = items_by_name["low table"]
        assert "contents" in table_summary, "Low table (surface: true) should have contents"
        assert len(table_summary["contents"]) == 1, (
            f"Low table should have exactly 1 item (the plate); "
            f"got {len(table_summary['contents'])}"
        )

        plate_in_ctx = table_summary["contents"][0]
        assert plate_in_ctx["name"] == "plate", (
            f"Item on low table should be the plate; got {plate_in_ctx['name']!r}"
        )
        assert "contents" in plate_in_ctx, (
            "Plate (surface: true) nested on low table should also have contents"
        )
        assert len(plate_in_ctx["contents"]) == 4, (
            f"Plate should show 4 rolls; got {len(plate_in_ctx['contents'])}"
        )
        roll_names = {c["name"] for c in plate_in_ctx["contents"]}
        assert roll_names == {"hot roll"}, (
            f"All items on plate should be hot rolls; got {roll_names}"
        )


@pytest.mark.llm
class TestItemContainerHierarchy:
    """
    Sequential scenario: kitchen → take rolls → plate → carry to Common Room → table.
    Each test checks item FK state after its turn.

    Do not run individual methods in isolation — run the full class with --llm.
    """

    # ------------------------------------------------------------------
    # Checkpoint 010: Initial state
    # ------------------------------------------------------------------

    def test_010_initial_state(self, item_db: Database, item_engine: GameEngine):
        """
        Verify the seeded container hierarchy before any turns run.
        Tray should have 12 rolls; plate should be empty; player in kitchen.
        """
        player = item_db.get_player_character(1)
        assert player["current_location_id"] == 2, (
            f"Player should start in Kitchen (2); got {player['current_location_id']}"
        )

        tray = item_by_name(item_db, "tray of hot rolls")
        assert tray is not None, "Tray of hot rolls should be seeded"
        assert tray["loc_id"] == 2, "Tray should be at loc_id=2 (Kitchen)"

        assert rolls_in_tray(item_db, tray["id"]) == 12, (
            "Tray should start with 12 rolls"
        )

        plate = item_by_name(item_db, "plate")
        assert plate is not None, "Plate should be seeded"
        assert plate["loc_id"] == 2, "Plate should be at loc_id=2 (Kitchen)"

        low_table = item_by_name(item_db, "low table")
        assert low_table is not None, "Low table should be seeded in Common Room"
        assert low_table["loc_id"] == 1, "Low table should be at loc_id=1 (Common Room)"

    # ------------------------------------------------------------------
    # Checkpoint 020: Player takes four rolls from tray and puts on plate
    # ------------------------------------------------------------------

    def test_020_take_rolls_and_place_on_plate(
        self, item_db: Database, item_engine: GameEngine
    ):
        """
        Player takes four rolls from the tray and places them on the plate
        in a single action. Pass 2 should emit item_transfers entries moving
        4 rolls from item_id=tray to item_id=plate. Eight rolls should remain
        in the tray.

        Note: testing the intermediate "in hand" state (rolls as char_id=1
        before placement) is deferred. Pass 2 may reasonably route rolls
        directly from tray to plate (skipping the in-hand step) when both
        are at the same location. Hand-slot capacity enforcement is also a
        pending design concern — we do not yet limit how many items can be
        in each slot.
        """
        tray = item_by_name(item_db, "tray of hot rolls")
        plate = item_by_name(item_db, "plate")

        prose = take_turn(
            item_engine,
            "take four rolls from the tray and place them on the plate",
        )
        assert prose, "Take-and-place turn should return prose"

        rolls_on_plate = item_db._rows(
            "SELECT * FROM item WHERE item_id = ? AND name = 'hot roll'",
            (plate["id"],),
        )
        remaining = rolls_in_tray(item_db, tray["id"])

        assert len(rolls_on_plate) == 4, (
            f"4 rolls should be on the plate (item_id={plate['id']}); "
            f"got {len(rolls_on_plate)}\n"
            f"Rolls remaining in tray: {remaining}\n"
            f"Prose: {prose[:300]}"
        )
        assert remaining == 8, (
            f"8 rolls should remain in the tray; got {remaining}\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 040: Player picks up the plate
    # ------------------------------------------------------------------

    def test_040_pick_up_plate(
        self, item_db: Database, item_engine: GameEngine
    ):
        """
        Player picks up the plate (which now holds 4 rolls).
        The plate should move from loc_id=2 to char_id=1.
        The rolls on the plate keep their item_id=plate relationship —
        they travel with the plate without individual transfers.
        """
        plate_before = item_by_name(item_db, "plate")

        prose = take_turn(
            item_engine,
            "pick up the plate with the rolls on it",
        )
        assert prose, "Pick-up turn should return prose"

        plate_after = item_by_name(item_db, "plate")
        assert plate_after["char_id"] == 1, (
            f"Plate should be held by player (char_id=1) after pickup; "
            f"plate.char_id={plate_after['char_id']}, "
            f"plate.loc_id={plate_after['loc_id']}\n"
            f"Prose: {prose[:300]}"
        )
        assert plate_after["loc_id"] is None, (
            "Plate loc_id should be NULL when held by player"
        )

        # Rolls should still be on the plate (item_id unchanged)
        rolls_still_on_plate = item_db._rows(
            "SELECT * FROM item WHERE item_id = ? AND name = 'hot roll'",
            (plate_after["id"],),
        )
        assert len(rolls_still_on_plate) == 4, (
            f"Rolls should still be on the plate after player picks it up; "
            f"got {len(rolls_still_on_plate)}\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 050: Player moves to the Common Room with the plate
    # ------------------------------------------------------------------

    def test_050_carry_plate_to_common_room(
        self, item_db: Database, item_engine: GameEngine
    ):
        """
        Player moves from the Kitchen to the Common Room. The plate is already
        char_id=1. Carried items travel with the character automatically —
        Pass 2 should NOT emit item_transfers for the plate just because the
        player moved. The plate should remain char_id=1 after arrival.
        """
        prose = take_turn(
            item_engine,
            "go to the common room",
        )
        assert prose, "Move turn should return prose"

        player = item_db.get_player_character(1)
        assert player["current_location_id"] == 1, (
            f"Player should be in Common Room (1) after move; "
            f"got {player['current_location_id']}\n"
            f"Prose: {prose[:300]}"
        )

        plate = item_by_name(item_db, "plate")
        assert plate["char_id"] == 1, (
            f"Plate should still be held by player (char_id=1) after moving rooms; "
            f"Pass 2 must not emit item_transfers for items already carried on movement.\n"
            f"plate.char_id={plate['char_id']}, plate.loc_id={plate['loc_id']}\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 060: Player puts the plate on the low table
    # ------------------------------------------------------------------

    def test_060_put_plate_on_low_table(
        self, item_db: Database, item_engine: GameEngine
    ):
        """
        Player places the plate (with rolls) on the low table by the fire.
        Pass 2 should emit an item_transfers entry with to_item_id=low_table_id.
        The plate should change from char_id=1 to item_id=low_table.
        The rolls remain on the plate (item_id=plate, unchanged).
        """
        low_table = item_by_name(item_db, "low table")

        prose = take_turn(
            item_engine,
            "set the plate of rolls on the low table by the fire",
        )
        assert prose, "Place turn should return prose"

        plate = item_by_name(item_db, "plate")
        assert plate["item_id"] == low_table["id"], (
            f"Plate should be on the low table (item_id={low_table['id']}); "
            f"got plate.item_id={plate['item_id']}, "
            f"plate.char_id={plate['char_id']}, "
            f"plate.loc_id={plate['loc_id']}\n"
            f"Prose: {prose[:300]}"
        )
        assert plate["char_id"] is None, (
            "Plate should no longer be held (char_id should be NULL)"
        )

        # Rolls should still be on the plate
        rolls_on_plate = item_db._rows(
            "SELECT * FROM item WHERE item_id = ? AND name = 'hot roll'",
            (plate["id"],),
        )
        assert len(rolls_on_plate) == 4, (
            f"Rolls should still be on the plate after it is set on the table; "
            f"got {len(rolls_on_plate)}\n"
            f"Prose: {prose[:300]}"
        )

        # Verify the full hierarchy: low_table → plate → 4 rolls
        # Low table is in Common Room (loc_id=1), confirmed by initial-state test.
        assert low_table["loc_id"] == 1, "Low table should remain in Common Room"
