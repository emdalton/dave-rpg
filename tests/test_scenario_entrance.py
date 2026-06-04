"""
tests/test_scenario_entrance.py — Hidden Hostel Full Scenario Test (Tier 2)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Tier 2 test: requires a live LLM (run with pytest --llm).
Requires: ANTHROPIC_API_KEY environment variable.

This file tests a complete play scenario from arrival at the hostel door through
dinner service, checking DB state at each significant checkpoint. It is the
primary regression test for the entrance flow, social interaction loop, and
timing mechanics introduced or changed across sessions 20–24.

Test numbering
--------------
Tests use three-digit numbers in steps of 10 (010, 020, ...) so new tests can
be inserted between existing ones without renumbering. Gaps are intentional.

Scenario outline
----------------
  010  Initial state: player outside (loc 6), description null, canister in pack
  020  Door refused: "open the door" → player stays at location 6
  030  Self-definition: player describes themselves and declares a travel almanac
       → player.description set; almanac instantiated via item_instantiations
  040  Enter hostel: "go inside" → player at Common Room (1)
  050  Greet Wanderer and Gin-chan: thank Wanderer; address Gin-chan as Gin-san
       and bow → hosts_of_the_hostel faction reputation rises above seed (0.40)
  055  Wanderer pending_intent cleared after greeting
  060  Go to kitchen: player at Kitchen (2)
  065  Pick up a roll from the tray → roll appears in Traveller inventory
  070  Make tea and bring with rolls to Gin-chan → Gin-chan attitude rises
  080  Go upstairs → arrive at Upper Corridor (3); first visit stops here
  085  Attempt to enter locked Room B → player stays in Upper Corridor (3)
  088  Enter Room A (4) to find Scholar; both corridor + Room A now visited
  090  Give almanac to Scholar → almanac leaves player inventory  [xfail: item_transfers]
  100  Scholar gives player a book → player gains new item          [xfail: item_transfers]
  110  Return to Common Room (1) and read (time passes)
  120  Advance clock past 8:30 PM → Marta's meal activity expires
  130  Go to kitchen, ask Marta about dinner → Marta mentions meal is ready
  140  Go upstairs, deliver dinner message to Scholar (and Soldier if present)

DB assertions (what each checkpoint checks)
-------------------------------------------
  010  player.current_location_id = 6; player.description IS NULL;
       Traveller has 'sencha canister' in character_item (almanac not yet seeded)
  020  player.current_location_id = 6  (door refused entry)
  030  player.description IS NOT NULL; 'travel almanac' (or similar) appears
       in character_item for the Traveller (item_instantiations)
  040  player.current_location_id = 1
  050  Traveller hosts_of_the_hostel reputation > 0.40 (seed value)
  055  Wanderer (id=3) pending_intent IS NULL
  060  player.current_location_id = 2
  065  Traveller inventory contains a roll item
  070  Gin-chan (id=6) surface attitude toward Traveller > seeded value
  080  player.current_location_id = 3 (Upper Corridor; first-visit stop)
  085  player.current_location_id = 3 (stayed in corridor; Room B is locked)
  088  player.current_location_id = 4
  090  [xfail] Traveller has no 'travel almanac' in character_item
  100  [xfail] Traveller has at least one item gained since step 090
  110  player.current_location_id = 1; game clock has advanced since step 040
  120  Marta (id=2) current_activity IS NULL
  130  Turn completes without error (prose output non-empty)
  140  Turn completes without error (action log grows after announcement turn)

Test ordering
-------------
Test methods within the class run in definition order. The module-scoped
`scenario_db` and `scenario_engine` fixtures persist state across methods, so
each test starts from where the previous one left off. Do not run individual
methods in isolation — earlier steps are prerequisites for later ones.

Known gaps marked with xfail
-----------------------------
Tests 090 and 100 cover item transfer mechanics (giving the almanac to the Scholar;
receiving a book in return). Pass 2 has no `item_transfers` outcome field yet —
it falls back to `item_changes` with a `slot` field, which the engine correctly
rejects. These tests document the expected DB outcome so they will pass
automatically once `item_transfers` is implemented (schema v10).
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from engine.db import Database
from engine.engine import GameEngine

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_SCHEMA_SQL = _REPO_ROOT / "schema" / "schema.sql"
_HOSTEL_SEED = _REPO_ROOT / "modules" / "hidden_hostel" / "seed.sql"


# =============================================================================
# Fixtures (module-scoped: state shared across all scenario tests)
# =============================================================================

@pytest.fixture(scope="module")
def scenario_db():
    """
    Build a Hidden Hostel database from schema + seed and yield a Database
    instance. Module-scoped so the same DB is used across all checkpoint tests
    in this file — state accumulates exactly as it would in a real play session.

    Teardown: closes the connection and deletes the temp file.
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
def scenario_engine(scenario_db):
    """
    Instantiate a GameEngine against the scenario DB using the real LLM client.
    Requires ANTHROPIC_API_KEY in the environment.

    Module-scoped so the engine instance (and its internal _player state) is
    shared across all checkpoint tests.
    """
    return GameEngine(db=scenario_db, game_id=1)


# =============================================================================
# Turn helper
# =============================================================================

def take_turn(engine: GameEngine, player_input: str) -> str:
    """
    Run one complete turn cycle as the real loop does:
      1. Check and clear expired NPC activities
      2. Run NPC wander rolls
      3. Refresh the player record (picks up any location changes from prior turn)
      4. Run the three-pass LLM turn

    Returns the prose output string.
    """
    engine._check_activity_expiry()
    engine._check_npc_wandering()
    engine._player = engine.db.get_player_character(engine.game_id)
    return engine._process_turn(player_input, involuntary_fired=[])


def get_player(engine: GameEngine) -> dict:
    """Return a fresh player record from the DB."""
    return engine.db.get_player_character(engine.game_id)


def get_inventory_names(db: Database, character_id: int) -> list[str]:
    """Return a list of item names held by a character."""
    rows = db._rows(
        "SELECT i.name FROM character_item ci "
        "JOIN item i ON ci.item_id = i.id "
        "WHERE ci.character_id = ?",
        (character_id,),
    )
    return [r["name"] for r in rows]


def get_ginchan_attitude(db: Database) -> float:
    """Return Gin-chan's (id=6) surface attitude toward the Traveller (id=1)."""
    row = db._row(
        "SELECT attitude FROM character_attitude "
        "WHERE character_id = 6 AND target_id = 1 AND attitude_type = 'surface'"
    )
    return row["attitude"] if row else 0.0


def get_traveller_faction_rep(db: Database, faction_name: str) -> float | None:
    """
    Return the Traveller's (id=1) reputation with the named faction, or None
    if no row exists. Looks up the faction by name within game_id=1.
    """
    faction = db.get_or_create_faction(game_id=1, name=faction_name)
    if not faction:
        return None
    row = db._row(
        "SELECT reputation FROM character_faction_reputation "
        "WHERE character_id = 1 AND faction_id = ?",
        (faction["id"],),
    )
    return row["reputation"] if row else None


# =============================================================================
# Scenario test class
# =============================================================================

@pytest.mark.llm
class TestHiddenHostelEntranceScenario:
    """
    Sequential scenario test. Methods run in definition order and share the
    module-scoped DB through scenario_db / scenario_engine fixtures.

    Each method is a named checkpoint; the scenario builds on prior state.
    Do not run methods individually — use `pytest tests/test_scenario_entrance.py --llm`.
    """

    # ------------------------------------------------------------------
    # Checkpoint 010: Verify seeded starting state
    # ------------------------------------------------------------------

    def test_010_initial_state(self, scenario_db: Database, scenario_engine: GameEngine):
        """
        The seeded starting state must match expected values before any turns run.

        Player starts outside (location 6), description null, with both the
        sencha canister and travel almanac in their pack.
        """
        player = get_player(scenario_engine)
        assert player["current_location_id"] == 6, (
            "Player should start at location 6 (Outside the Hostel Door)"
        )
        assert player["description"] is None, (
            "Player description should be NULL before self-definition"
        )

        inv = get_inventory_names(scenario_db, character_id=1)
        assert "sencha canister" in inv, "Sencha canister should be in starting pack"
        # The travel almanac is NOT pre-seeded — it will be instantiated in test 03
        # when the player declares it during self-definition. Only the canister is
        # seeded; the almanac tests the item_instantiations outcome handler.

        door = scenario_db.get_character(7)
        assert door is not None, "Blue Door (id=7) should exist"
        pending = door.get("pending_intent") or ""
        assert "describe themselves" in pending, (
            "Blue Door pending_intent should ask traveller to describe themselves"
        )

    # ------------------------------------------------------------------
    # Checkpoint 020: Door refuses entry before self-definition
    # ------------------------------------------------------------------

    def test_020_door_refused_before_definition(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        Attempting to open or enter the door before self-definition must not
        move the player. The door's pending_intent gates entry on
        player.description being non-null.
        """
        prose = take_turn(scenario_engine, "open the door")
        assert prose, "Turn should return non-empty prose"

        player = get_player(scenario_engine)
        assert player["current_location_id"] == 6, (
            "Player should still be at location 6 after door refuses entry "
            f"(got location {player['current_location_id']})\n"
            f"Prose: {prose[:200]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 030: Self-definition at the mirror
    # ------------------------------------------------------------------

    def test_030_self_definition_and_item_instantiation(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        When the player describes themselves and mentions a carried item, Pass 2
        should emit both player_character_update (writing description to DB) and
        item_instantiations (creating the declared item in the player's inventory).

        The travel almanac is NOT pre-seeded. Declaring it here tests the
        item_instantiations outcome handler — the engine should create the item
        and place it in the player's pack without a seed entry.
        """
        inv_before = set(get_inventory_names(scenario_db, character_id=1))

        prose = take_turn(
            scenario_engine,
            "I am a woman of middle years with dark hair in a practical braid, "
            "wearing a worn travelling coat. I carry a battered leather pack — "
            "inside there is a travel almanac, well-thumbed, and a tin of tea.",
        )
        assert prose, "Self-definition turn should return prose"

        # player.description must be written
        player = get_player(scenario_engine)
        assert player["description"] is not None, (
            "player.description should be set after self-definition turn\n"
            f"Prose: {prose[:300]}"
        )

        # The almanac should now exist in inventory (item_instantiations)
        inv_after = set(get_inventory_names(scenario_db, character_id=1))
        new_items = inv_after - inv_before
        assert any("almanac" in name.lower() for name in new_items), (
            "A travel almanac should have been instantiated in the player's inventory "
            "when declared during self-definition\n"
            f"Inventory before: {inv_before}\n"
            f"Inventory after:  {inv_after}\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 040: Enter the hostel
    # ------------------------------------------------------------------

    def test_040_enter_hostel(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        After self-definition, entering the door should move the player to
        the Common Room (location 1). The door's pending_intent condition is
        now satisfied (player.description is non-null).
        """
        prose = take_turn(scenario_engine, "go inside")
        assert prose, "Entry turn should return prose"

        player = get_player(scenario_engine)
        assert player["current_location_id"] == 1, (
            f"Player should be in Common Room (1) after entering; "
            f"got location {player['current_location_id']}\n"
            f"Prose: {prose[:200]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 050: Greet Wanderer and Gin-chan — faction reputation test
    # ------------------------------------------------------------------

    def test_050_greet_wanderer_and_ginchan(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        The Wanderer greets the newly arrived Traveller in the Common Room.
        The player responds by thanking the Wanderer warmly, then turns to
        Gin-chan and addresses them as 'Gin-san' with a respectful bow.

        Using an honorific and bowing to a permanent resident on first meeting
        is a culturally attentive gesture that fits hostel norms. Pass 2 should
        issue a faction_reputation_changes entry raising the Traveller's standing
        with hosts_of_the_hostel above the seeded value of 0.40.

        This is the primary Tier 2 test for the faction reputation system.
        """
        baseline = get_traveller_faction_rep(scenario_db, "hosts_of_the_hostel")
        assert baseline is not None, (
            "Traveller should have a hosts_of_the_hostel reputation row from seed"
        )

        prose = take_turn(
            scenario_engine,
            "thank the Wanderer warmly for the welcome, then turn to Gin-chan, "
            "address them as Gin-san, and offer a respectful bow",
        )
        assert prose, "Greeting turn should return prose"

        final = get_traveller_faction_rep(scenario_db, "hosts_of_the_hostel")
        assert final is not None, (
            "Traveller's hosts_of_the_hostel reputation row should still exist after turn"
        )
        assert final > baseline, (
            f"Respectful greeting with honorific and bow should raise "
            f"hosts_of_the_hostel reputation "
            f"(baseline={baseline:.3f}, final={final:.3f})\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 055: Wanderer pending_intent cleared after greeting
    # ------------------------------------------------------------------

    def test_055_wanderer_pending_intent_cleared(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        The Wanderer's pending_intent was seeded to greet the newly arrived
        Traveller and introduce Gin-chan. After the greeting turn in test_050,
        Pass 2 should have cleared it (or the engine should have cleared it on
        fulfillment). This test verifies the discharge actually happened.

        A non-null pending_intent after fulfillment would mean the engine is
        not writing back the cleared value, or Pass 2 is not issuing a
        pending_intent_updates entry for the Wanderer.
        """
        wanderer = scenario_db.get_character(3)
        assert wanderer["pending_intent"] is None, (
            "Wanderer's pending_intent should be cleared after greeting the Traveller "
            f"(current value: {wanderer['pending_intent']!r})"
        )

    # ------------------------------------------------------------------
    # Checkpoint 060: Navigate to the kitchen
    # ------------------------------------------------------------------

    def test_060_go_to_kitchen(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """Player should be able to move from Common Room to Kitchen (2)."""
        prose = take_turn(scenario_engine, "go to the kitchen")
        assert prose, "Kitchen move should return prose"

        player = get_player(scenario_engine)
        assert player["current_location_id"] == 2, (
            f"Player should be in Kitchen (2); got {player['current_location_id']}\n"
            f"Prose: {prose[:200]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 065: Pick up a roll from the tray
    # ------------------------------------------------------------------

    def test_065_pick_up_roll_from_tray(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        The kitchen contains a seeded 'tray of hot rolls' (location_id=2).
        The player takes one. Pass 2 should issue an item_changes entry that
        moves a roll into the Traveller's inventory.

        This tests the v9 item_changes handler for location → character
        transfers (before item_transfers is implemented). The roll is a
        consumable, so any item with 'roll' in the name appearing in the
        Traveller's character_item rows constitutes a pass.
        """
        inv_before = set(get_inventory_names(scenario_db, character_id=1))

        prose = take_turn(
            scenario_engine,
            "take a couple of rolls from the tray on the worktable",
        )
        assert prose, "Taking rolls should return prose"

        inv_after = set(get_inventory_names(scenario_db, character_id=1))
        new_items = inv_after - inv_before
        assert any("roll" in name.lower() for name in new_items), (
            "Taking rolls from the tray should add a roll item to Traveller inventory\n"
            f"Inventory before: {inv_before}\n"
            f"Inventory after:  {inv_after}\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 070: Tea and rolls — Gin-chan attitude test
    # ------------------------------------------------------------------

    def test_070_tea_and_rolls_for_ginchan(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        Making tea and bringing it with rolls to Gin-chan should raise
        Gin-chan's surface attitude above the seeded value of 0.50.

        This takes two turns: prepare the tea in the kitchen, then carry
        the tea and rolls to the Common Room and offer them to Gin-chan.
        The exact action text matters less than whether the final attitude
        reflects the kind gesture.
        """
        baseline = get_ginchan_attitude(scenario_db)

        # Turn 1: offer to make tea for Gin-chan
        take_turn(scenario_engine, "offer to make tea for Gin-chan using my sencha canister")

        # Turn 2: go to Common Room carrying tea and rolls, offer to Gin-chan
        take_turn(scenario_engine, "go to the common room")
        prose = take_turn(
            scenario_engine,
            "offer Gin-chan the tea and take a couple of rolls from the tray for us to share",
        )
        assert prose, "Offer turn should return prose"

        final = get_ginchan_attitude(scenario_db)
        assert final > baseline, (
            f"Gin-chan attitude should increase after tea + rolls offer "
            f"(baseline={baseline:.3f}, final={final:.3f})\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 080: Go upstairs to find the Scholar
    # ------------------------------------------------------------------

    def test_080_go_upstairs_to_corridor(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        "Go upstairs" moves the player from Common Room (1) to Upper Corridor
        (3) via the staircase connection. This is the player's first visit to
        the corridor — the engine stops here because Room A has not yet been
        visited, so multi-hop BFS to Room A is blocked.

        With the Old Soldier in the Common Room, the corridor is empty, so
        there is no NPC interruption. The stop is a first-visit exploration
        step, not a social one.

        Stopping here first serves two purposes: it sets up test_085 (locked
        Room B attempt from the corridor) and records the corridor as visited,
        which later enables the unobstructed two-hop return in test_110.
        """
        take_turn(scenario_engine, "go upstairs")

        player = get_player(scenario_engine)
        assert player["current_location_id"] == 3, (
            f"Player should arrive at Upper Corridor (3) on first upstairs move; "
            f"got location {player['current_location_id']}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 085: Attempt locked Room B — player stays in corridor
    # ------------------------------------------------------------------

    def test_085_locked_room_b(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        Room B (location 5) is connected to Upper Corridor (3) via a door
        with is_passable=0. The passage_note records that the door has no
        handle on the corridor side and has not opened in living memory.

        The player is already in Upper Corridor (3) after test_080. Attempting
        to enter Room B must leave the player at location 3.

        Tests the is_passable=0 branch of the pathfinding layer. Also confirms
        that the engine returns prose explaining the failure (Pass 3 renders
        the impassable connection) rather than silently doing nothing.
        """
        prose = take_turn(scenario_engine, "try the door to Room B")
        assert prose, "Locked door attempt should return prose"

        player = get_player(scenario_engine)
        assert player["current_location_id"] == 3, (
            "Player should remain in Upper Corridor after attempting locked Room B\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 088: Enter Room A to find the Scholar
    # ------------------------------------------------------------------

    def test_088_find_scholar_in_room_a(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        From Upper Corridor (3), "go to Room A" is a single adjacent hop.
        The visited check is skipped for adjacent moves, so the player arrives
        directly. This turn records Room A as visited; combined with Upper
        Corridor (visited in test_080), both hops of the return route are now
        known, enabling the unobstructed two-hop descent in test_110.
        """
        take_turn(scenario_engine, "go to Room A")

        player = get_player(scenario_engine)
        assert player["current_location_id"] == 4, (
            f"Player should be in Room A (4) to find the Scholar; "
            f"got {player['current_location_id']}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 090: Give travel almanac to Scholar
    # xfail: item_transfers outcome field not yet implemented (schema v10)
    # ------------------------------------------------------------------

    @pytest.mark.xfail(
        reason=(
            "item_transfers outcome field not yet implemented. "
            "Pass 2 uses item_changes with slot field, which the engine rejects. "
            "This test will pass once schema v10 and item_transfers are in place."
        ),
        strict=False,
    )
    def test_090_give_almanac_to_scholar(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        Giving the travel almanac to the Scholar should remove it from the
        Traveller's inventory. Currently fails because item_transfers is not
        implemented — the engine rejects item_changes with a slot field.
        """
        prose = take_turn(
            scenario_engine,
            "offer the travel almanac to the Scholar — they seem like someone who would appreciate it",
        )
        assert prose, "Almanac offer should return prose"

        inv = get_inventory_names(scenario_db, character_id=1)
        assert "travel almanac" not in inv, (
            "Travel almanac should leave player inventory after being given to Scholar\n"
            f"Current inventory: {inv}\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 100: Scholar gives player a book in return
    # xfail: item_transfers outcome field not yet implemented (schema v10)
    # ------------------------------------------------------------------

    @pytest.mark.xfail(
        reason=(
            "item_transfers outcome field not yet implemented. "
            "Scholar cannot give an item to the player without item_transfers. "
            "This test will pass once schema v10 and item_transfers are in place."
        ),
        strict=False,
    )
    def test_100_scholar_gives_book(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        After receiving the almanac, the Scholar should offer a book in return.
        The Traveller should gain a new item. The specific item name is not
        checked — any new item in inventory counts.
        """
        inv_before = set(get_inventory_names(scenario_db, character_id=1))

        prose = take_turn(
            scenario_engine,
            "thank the Scholar and ask if they have anything they'd like to share in return",
        )
        assert prose, "Exchange turn should return prose"

        inv_after = set(get_inventory_names(scenario_db, character_id=1))
        new_items = inv_after - inv_before
        assert new_items, (
            "Traveller should receive at least one new item from the Scholar\n"
            f"Inventory before: {inv_before}\n"
            f"Inventory after:  {inv_after}\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 110: Return to Common Room and read (time passes)
    # ------------------------------------------------------------------

    def test_110_return_and_read(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        Player returns to the Common Room and reads by the fire. After the LLM
        turn, we explicitly set a reading activity on the player with a
        calibrated duration so that it expires after Marta's meal deadline
        (clock 1230, i.e. 8:30 PM).

        Specifically: duration = (1230 - current_clock) + 15, so the reading
        expires at clock 1245 regardless of where the clock currently sits.
        This gives test_11 a reliable, query-able expiry to advance toward
        while guaranteeing the clock will also be past Marta's threshold.
        """
        take_turn(scenario_engine, "go back downstairs to the Common Room")

        # With the Old Soldier moved to the Common Room, Upper Corridor (3) is
        # empty. The player visited it on the way up (test_08), so the engine
        # should complete the full Room A (4) → Upper Corridor (3) → Common
        # Room (1) route in a single turn without interruption.
        player = get_player(scenario_engine)
        assert player["current_location_id"] == 1, (
            f"Multi-hop return from Room A should complete uninterrupted — "
            f"Upper Corridor is empty and already visited; "
            f"got location {player['current_location_id']}"
        )

        prose = take_turn(scenario_engine, "sit by the fire and read")
        assert prose, "Reading turn should return prose"

        # Pin a deterministic reading activity on the player so test_11 has a
        # reliable expiry time to advance toward.
        instance = scenario_db.get_active_instance(game_id=1)
        clock_now = instance["current_time_minutes"]
        # Expire 15 minutes after Marta's 8:30 PM deadline, whatever the
        # current clock time is.
        read_duration = (1230 - clock_now) + 15
        scenario_db.set_character_activity(
            character_id=1,
            activity="reading by the fire",
            started_at=clock_now,
            duration_minutes=read_duration,
            confidence=0.80,
            renewable=0,
        )

    # ------------------------------------------------------------------
    # Checkpoint 120: Marta's meal timing — activity expires at 8:30 PM
    # ------------------------------------------------------------------

    def test_120_marta_meal_ready_at_deadline(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        Verify that _check_activity_expiry() clears both the player's reading
        and Marta's meal preparation when the game clock advances past their
        respective deadlines.

        test_110 set a reading activity on the player (id=1) expiring at
        clock 1245 (15 min after Marta's 8:30 PM deadline). This test:
          1. Reads activity_started_at + activity_estimated_duration from both
             characters to compute their expiry times.
          2. Advances the clock to max(player_expiry, marta_expiry) + 1.
          3. Fires _check_activity_expiry().
          4. Asserts both current_activity fields are now NULL.

        This exercises the activity_estimated_duration field end-to-end,
        confirming that the engine derives expiry from stored data rather than
        relying on hard-coded thresholds.
        """
        player_before = scenario_db.get_character(1)
        marta_before = scenario_db.get_character(2)

        # Compute expiry clock values from stored activity fields.
        player_expiry = (
            player_before["activity_started_at"] + player_before["activity_estimated_duration"]
            if player_before.get("activity_started_at") is not None
               and player_before.get("activity_estimated_duration") is not None
            else 0
        )
        marta_expiry = (
            marta_before["activity_started_at"] + marta_before["activity_estimated_duration"]
            if marta_before.get("activity_started_at") is not None
               and marta_before.get("activity_estimated_duration") is not None
            else 0
        )
        target_clock = max(player_expiry, marta_expiry) + 1

        instance = scenario_db.get_active_instance(game_id=1)
        current_time = instance["current_time_minutes"]
        advance_by = max(1, target_clock - current_time)
        scenario_db.advance_game_clock(instance["id"], elapsed_minutes=advance_by)

        scenario_engine._check_activity_expiry()

        player_after = scenario_db.get_character(1)
        marta_after = scenario_db.get_character(2)

        assert player_after.get("current_activity") is None, (
            "Player's reading activity should be cleared after clock passes expiry "
            f"(started={player_before.get('activity_started_at')}, "
            f"duration={player_before.get('activity_estimated_duration')}, "
            f"target_clock={target_clock})"
        )
        assert marta_after.get("current_activity") is None, (
            "Marta's meal activity should be cleared after clock passes 8:30 PM "
            f"(started={marta_before.get('activity_started_at')}, "
            f"duration={marta_before.get('activity_estimated_duration')}, "
            f"target_clock={target_clock})"
        )

    # ------------------------------------------------------------------
    # Checkpoint 130: Ask Marta about dinner
    # ------------------------------------------------------------------

    def test_130_marta_mentions_dinner(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        After Marta's activity expires, interacting with her in the kitchen
        should produce a response related to dinner being ready. We check
        only that the turn completes and returns non-empty prose — prose
        quality is a Tier 3 concern.
        """
        # Navigate to kitchen if not already there.
        player = get_player(scenario_engine)
        if player["current_location_id"] != 2:
            take_turn(scenario_engine, "go to the kitchen")

        prose = take_turn(
            scenario_engine,
            "tell Marta the meal smells wonderful and ask if dinner is nearly ready",
        )
        assert prose, "Kitchen interaction after meal expiry should return non-empty prose"

    # ------------------------------------------------------------------
    # Checkpoint 140: Deliver dinner message to the Scholar
    # ------------------------------------------------------------------

    def test_140_deliver_dinner_message(
        self, scenario_db: Database, scenario_engine: GameEngine
    ):
        """
        Player goes upstairs and tells the Scholar that dinner is ready.
        The Scholar is in Room A (4). We check that the action log grows —
        i.e. the turn was processed and written — not the NPC response (Tier 3).

        NOTE — test gap: the Old Soldier is in the Common Room (1) and this
        test does not verify she receives the message or reacts. A more complete
        version of this test would go back downstairs, tell the Soldier directly,
        and assert her emotional_state or attitude shifts in response. Left for
        a future session when multi-room message delivery and NPC reaction
        chaining are more thoroughly exercised.

        FUTURE TEST IDEA: when the Wanderer greets the newly arrived player and
        introduces Gin-chan, if the Wanderer also mentions the Old Soldier (who
        is now visible in the Common Room), the Soldier should react — at minimum
        a visible attitude or emotional_state shift, given her distrust of
        strangers and negative attitude toward the Wanderer (-0.40). This is a
        Tier 3 / LLM-eval concern (prose quality + attitude delta), not Tier 2.
        """
        log_count_before = scenario_db._row(
            "SELECT COUNT(*) AS n FROM action_log WHERE game_id = 1",
        )["n"]

        # Go upstairs and announce dinner.
        take_turn(scenario_engine, "go upstairs")
        prose = take_turn(
            scenario_engine,
            "call out to the Scholar and the Soldier that Marta says dinner is ready",
        )
        assert prose, "Dinner announcement should return non-empty prose"

        log_count_after = scenario_db._row(
            "SELECT COUNT(*) AS n FROM action_log WHERE game_id = 1",
        )["n"]
        assert log_count_after > log_count_before, (
            "Action log should have new entries after the dinner announcement turn"
        )
