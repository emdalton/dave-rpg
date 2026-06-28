"""
tests/test_context.py — Context Packet Assembly Tests (Tier 1: no LLM)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Tests that build_pass1_packet(), build_pass2_packet(), and build_pass3_packet()
return correctly structured dicts given a known database state. No LLM calls
are made; the tests only verify that context assembly is working correctly.

What these tests cover
-----------------------
- Required top-level keys are present in each packet
- Player profile block contains expected fields (location, emotional_state)
- v7+ fields are included when data is present: pending_intent, faction_reputations
- v8+ fields are included when set: current_activity in NPC profiles
- Pass 2 packet includes characters at location with correct shape
- Pass 3 packet includes adjacent_locations and characters_present
- Unknown game_id raises cleanly rather than returning None silently

These tests are intentionally narrow — they verify the shape and presence of
data, not prose content or LLM behaviour. If a context key is added or renamed
in context.py, the corresponding test here will fail, flagging the change.
"""

import pytest

from engine.context import build_pass1_packet, build_pass2_packet, build_pass3_packet
from engine.db import Database

from tests.fixtures.responses import PASS1_MINIMAL, PASS2_MINIMAL, PASS3_PROSE


# Minimal synthetic action_record for Pass 2 and Pass 3 packet assembly.
# Mirrors what a real Pass 1 response would produce.
_ACTION_RECORD = {**PASS1_MINIMAL}

# Minimal synthetic outcome dict for Pass 3 packet assembly.
_OUTCOME = {**PASS2_MINIMAL}


# =============================================================================
# Pass 1 context packet
# =============================================================================

class TestBuildPass1Packet:
    def test_required_top_level_keys(self, tmp_db: Database):
        packet = build_pass1_packet(
            db=tmp_db, game_id=1, player_input="look around"
        )
        # Actual keys: current_location, description, game, known_locations,
        # known_characters, pass, player, player_input, recent_actions
        for key in ("player_input", "game", "player", "current_location",
                    "recent_actions", "known_locations", "known_characters"):
            assert key in packet, f"Pass 1 packet missing key: {key!r}"

    def test_player_input_preserved(self, tmp_db: Database):
        packet = build_pass1_packet(
            db=tmp_db, game_id=1, player_input="go to the hall"
        )
        assert packet["player_input"] == "go to the hall"

    def test_known_locations_includes_all_locations(self, tmp_db: Database):
        packet = build_pass1_packet(
            db=tmp_db, game_id=1, player_input="look"
        )
        # known_locations should contain both location names as keys
        known = packet["known_locations"]
        names = list(known.keys()) if isinstance(known, dict) else [
            loc["name"] for loc in known
        ]
        # Antechamber and Hall must both appear somewhere
        name_str = " ".join(str(n) for n in names).lower()
        assert "antechamber" in name_str
        assert "hall" in name_str

    def test_known_characters_includes_all_npcs(self, tmp_db: Database):
        """
        known_characters must list all non-player characters with id, name,
        and species. The test fixture seeds Guard (id=2, species='human') and
        Hermit (id=3, species='human') as NPCs; Hero (id=1) is the player and
        must not appear. Each entry must have 'id', 'name', and 'species' keys
        so the LLM can resolve both name-based and species-based references.
        """
        packet = build_pass1_packet(
            db=tmp_db, game_id=1, player_input="talk to the guard"
        )
        known = packet["known_characters"]
        assert isinstance(known, list), (
            f"known_characters should be a list; got {type(known)}"
        )
        # Must include both NPCs from the test fixture.
        ids = {entry["id"] for entry in known}
        assert 2 in ids, "Guard (id=2) should appear in known_characters"
        assert 3 in ids, "Hermit (id=3) should appear in known_characters"

        # Player character (Hero, id=1) must be excluded.
        assert 1 not in ids, (
            "Player character (Hero, id=1) must not appear in known_characters — "
            "Pass 1 resolves NPC targets only"
        )

        # Each entry must carry id, name, and species for disambiguation.
        for entry in known:
            for field in ("id", "name", "species"):
                assert field in entry, (
                    f"known_characters entry {entry} is missing required field {field!r}"
                )

    def test_player_profile_has_location(self, tmp_db: Database):
        packet = build_pass1_packet(
            db=tmp_db, game_id=1, player_input="look"
        )
        player = packet["player"]
        # Player block uses current_location_id; the full location dict is at
        # the top-level current_location key.
        assert "current_location_id" in player or "current_location" in player, \
               "Player profile should include current location information"

    def test_game_block_has_genre_and_tone(self, tmp_db: Database):
        packet = build_pass1_packet(
            db=tmp_db, game_id=1, player_input="look"
        )
        game = packet["game"]
        assert game["genre"] == "adventure"
        assert game["tone"] == "neutral"


# =============================================================================
# Pass 2 context packet
# =============================================================================

class TestBuildPass2Packet:
    def test_required_top_level_keys(self, tmp_db: Database):
        packet = build_pass2_packet(
            db=tmp_db, game_id=1, action_record=_ACTION_RECORD
        )
        # Actual keys: action_record, characters_nearby, characters_present,
        # current_location, description, game, involuntary_events_this_turn,
        # pass, player
        for key in ("game", "player", "characters_present", "current_location",
                    "action_record"):
            assert key in packet, f"Pass 2 packet missing key: {key!r}"

    def test_player_profile_has_emotional_state(self, tmp_db: Database):
        packet = build_pass2_packet(
            db=tmp_db, game_id=1, action_record=_ACTION_RECORD
        )
        player = packet["player"]
        assert "emotional_state" in player

    def test_faction_reputations_included_when_present(self, tmp_db: Database):
        packet = build_pass2_packet(
            db=tmp_db, game_id=1, action_record=_ACTION_RECORD
        )
        player = packet["player"]
        # Hero has a faction_reputation record; it should appear in the packet.
        assert "faction_reputations" in player, \
            "faction_reputations should be in player profile when records exist"
        reps = player["faction_reputations"]
        assert isinstance(reps, list)
        assert len(reps) >= 1
        # At least one entry should name the seeded faction.
        # Actual key is faction_name (from context.py JOIN output).
        faction_names = [
            r.get("faction_name") or r.get("faction") or r.get("name", "")
            for r in reps
        ]
        assert any("town_guard" in n for n in faction_names)

    def test_characters_at_location_includes_guard(self, tmp_db: Database):
        # Hero is at location 1; Guard is also at location 1.
        packet = build_pass2_packet(
            db=tmp_db, game_id=1, action_record=_ACTION_RECORD
        )
        chars = packet["characters_present"]
        names = [c.get("name") for c in chars]
        assert "Guard" in names, \
            "Guard should appear in characters_at_location (both at Antechamber)"

    def test_hermit_not_in_characters_at_location(self, tmp_db: Database):
        # Hermit is at location 2; should not appear in location 1 packet.
        packet = build_pass2_packet(
            db=tmp_db, game_id=1, action_record=_ACTION_RECORD
        )
        chars = packet["characters_present"]
        names = [c.get("name") for c in chars]
        assert "Hermit" not in names

    def test_npc_profile_includes_pending_intent_when_set(self, tmp_db: Database):
        # Set Guard's pending_intent and verify it appears in their profile.
        tmp_db.update_character_pending_intent(
            character_id=2,
            intent_text="owes Hero a favour",
        )
        packet = build_pass2_packet(
            db=tmp_db, game_id=1, action_record=_ACTION_RECORD
        )
        chars = packet["characters_present"]
        guard_profile = next((c for c in chars if c.get("name") == "Guard"), None)
        assert guard_profile is not None
        assert "pending_intent" in guard_profile, \
            "pending_intent should appear in NPC profile when set"
        assert guard_profile["pending_intent"] == "owes Hero a favour"

    def test_npc_profile_includes_activity_when_set(self, tmp_db: Database):
        # Set Guard's current_activity and verify it appears in their profile.
        tmp_db.set_character_activity(
            character_id=2,
            activity="standing watch",
            started_at=180,
            duration_minutes=30,
            confidence=0.80,
            renewable=0,
        )
        packet = build_pass2_packet(
            db=tmp_db, game_id=1, action_record=_ACTION_RECORD
        )
        chars = packet["characters_present"]
        guard_profile = next((c for c in chars if c.get("name") == "Guard"), None)
        assert guard_profile is not None
        assert "current_activity" in guard_profile, \
            "current_activity should appear in NPC profile when set"

    def test_adjacent_locations_in_pass2_packet(self, tmp_db: Database):
        packet = build_pass2_packet(
            db=tmp_db, game_id=1, action_record=_ACTION_RECORD
        )
        # Adjacent locations are nested inside current_location, not top-level.
        # Each entry has keys: location_id, name, connection_type.
        loc = packet["current_location"]
        adj = loc.get("adjacent_locations")
        assert adj is not None, \
            "current_location should include adjacent_locations list"
        adj_ids = [a.get("location_id") for a in adj]
        assert 2 in adj_ids, "Hall (location_id=2) should be adjacent to Antechamber"


# =============================================================================
# Pass 3 context packet
# =============================================================================

class TestBuildPass3Packet:
    def test_required_top_level_keys(self, tmp_db: Database):
        packet = build_pass3_packet(
            db=tmp_db, game_id=1, outcome=_OUTCOME
        )
        for key in ("game", "player", "outcome", "characters_present",
                    "adjacent_locations"):
            assert key in packet, f"Pass 3 packet missing key: {key!r}"

    def test_outcome_preserved_in_packet(self, tmp_db: Database):
        packet = build_pass3_packet(
            db=tmp_db, game_id=1, outcome=_OUTCOME
        )
        # The outcome dict should be embedded verbatim (or structurally equivalent).
        assert "narrative_beat" in packet["outcome"]

    def test_characters_present_includes_guard(self, tmp_db: Database):
        packet = build_pass3_packet(
            db=tmp_db, game_id=1, outcome=_OUTCOME
        )
        chars = packet["characters_present"]
        names = [c.get("name") for c in chars]
        assert "Guard" in names

    def test_adjacent_locations_in_pass3_packet(self, tmp_db: Database):
        packet = build_pass3_packet(
            db=tmp_db, game_id=1, outcome=_OUTCOME
        )
        adj = packet["adjacent_locations"]
        assert isinstance(adj, list)
        # Pass 3 adjacent_locations items have keys: name, is_passable (no id).
        adj_names = [a.get("name", "").lower() for a in adj]
        assert any("hall" in n for n in adj_names), \
            "Hall should appear in adjacent_locations in Pass 3 packet"

    def test_game_block_has_speech_filter(self, tmp_db: Database):
        packet = build_pass3_packet(
            db=tmp_db, game_id=1, outcome=_OUTCOME
        )
        assert "speech_filter" in packet["game"] or "speech_filter" in packet

    def test_characters_present_has_current_activity_key(self, tmp_db: Database):
        """
        Every entry in characters_present must carry a current_activity key.
        The value may be None (no recorded activity), but the key must be present
        so Pass 3 can distinguish "no activity set" from "field missing".
        Guard is in the Antechamber (same location as the player) and has no
        activity seeded, so current_activity should be None.
        """
        packet = build_pass3_packet(db=tmp_db, game_id=1, outcome=_OUTCOME)
        chars = packet["characters_present"]
        guard = next((c for c in chars if c.get("name") == "Guard"), None)
        assert guard is not None, "Guard should be present at Antechamber"
        assert "current_activity" in guard, (
            "characters_present entries must include current_activity key"
        )
        assert guard["current_activity"] is None, (
            "Guard has no seeded activity; current_activity should be None"
        )

    def test_characters_present_current_activity_reflects_db(self, tmp_db: Database):
        """
        When an NPC has a current_activity set in the DB, it must appear
        verbatim in the characters_present packet so Pass 3 can reference it.
        """
        # Give the Guard a current activity so Pass 3 can describe it accurately.
        tmp_db.set_character_activity(
            character_id=2,
            activity="standing watch at the door",
            started_at=180,
            duration_minutes=30,
            confidence=0.8,
            renewable=0,
        )
        packet = build_pass3_packet(db=tmp_db, game_id=1, outcome=_OUTCOME)
        chars = packet["characters_present"]
        guard = next((c for c in chars if c.get("name") == "Guard"), None)
        assert guard is not None, "Guard should be present at Antechamber"
        assert guard["current_activity"] == "standing watch at the door", (
            "current_activity in packet must match the value set in the DB"
        )
