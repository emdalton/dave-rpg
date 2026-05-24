-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v6 → v7
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Reason: Four additions required before Meryton module seed work begins.
--
-- 1. faction table.
--    The Meryton/P&P module requires reputation tracking per social group,
--    not a single global reputation float. Elizabeth's standing with the
--    Bennet family, the Meryton neighborhood, and the Bingley circle are
--    meaningfully distinct and can diverge — this tension only has mechanical
--    weight if factions are tracked as separate entities.
--
--    Factions are module-scoped: game_id is the isolation boundary between
--    modules that share a database. A module with no factions (e.g. I Am a
--    Cat) has no rows for its game_id.
--
--    Factions may also be created dynamically during play. A new family unit
--    formed by marriage, a political alliance that coalesces as events unfold,
--    or a splinter group that emerges from player choices are all valid faction
--    creation events. Pass 2 issues a create_faction field in its outcome JSON;
--    the engine inserts the row before applying any reputation changes.
--
-- 2. character_faction_reputation table.
--    Tracks a character's standing with each faction as a float (0.0–1.0).
--    Distinct from allegiance, which is motivational: a character's drive
--    toward or identification with a faction is modeled via MST goals in
--    character_goal (e.g. a 'belonging' goal whose description names the
--    faction). Reputation is how the faction views the character; allegiance
--    is how the character relates to the faction. The two work together
--    without redundancy.
--
-- 3. passage_note on location_connection.
--    The location graph must distinguish locked connections (physically
--    impassable) from convention-closed connections (socially impassable —
--    the cost of entry is reputation damage, not physical incapability). The
--    existing is_passable flag is the engine's binary movement gate; this
--    new field gives Pass 2 the semantic context to adjudicate the distinction.
--
-- 4. pending_intent on character.
--    A working-memory slot for deferred social obligations and queued
--    intentions. Prerequisite for dance card mechanics, multi-turn social
--    commitments, and hidden agendas (e.g. Wickham). Consistent with the
--    equity and belonging goal categories in the Ford-Nichols MST framework.
--
-- Usage (existing database at v6):
--   sqlite3 path/to/your.db < schema/migrations/migrate_v6_to_v7.sql
--
-- For a fresh install, run schema.sql (which incorporates all fields through
-- v7) then the module seed files. Migrations are only needed for existing
-- databases being upgraded in place.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. faction
-- -----------------------------------------------------------------------------

-- Named social groups whose opinion of a character has mechanical weight.
-- Scoped to a game module via game_id. Each module defines its own faction
-- set; game_id is the isolation boundary when multiple modules share a DB.
--
-- The description field is written for the LLM: it should explain what this
-- faction values, how it judges characters, and what kinds of actions raise
-- or lower standing. Write as if briefing the adjudicator on the faction's
-- perspective and priorities. This text is passed verbatim to Pass 2 in the
-- faction_reputations block of the context packet.
--
-- Factions may be created during play (see migration header, point 1).
-- The engine handles dynamic creation by accepting a create_faction entry
-- in Pass 2 outcome JSON and inserting a row here before writing reputation
-- changes.
CREATE TABLE faction (
    id          INTEGER PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES game(id),

    -- Short slug used as a key in context packets and Pass 2 outcome JSON.
    -- Use snake_case. Examples: 'bennet_family', 'meryton_neighborhood',
    -- 'bingley_circle'. Must be unique within a game_id (see constraint below).
    name        TEXT    NOT NULL,

    -- LLM-facing description of this faction's values and judgment criteria.
    -- Passed to Pass 2 in the faction_reputations context block.
    description TEXT    NOT NULL,

    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Faction slugs must be unique within a module. Slugs are used as keys
    -- in outcome JSON; collisions within a game_id would be ambiguous.
    UNIQUE(game_id, name)
);

CREATE INDEX idx_faction_game ON faction(game_id);


-- -----------------------------------------------------------------------------
-- 2. character_faction_reputation
-- -----------------------------------------------------------------------------

-- A character's standing with a faction, as a float in [0.0, 1.0].
--   0.0 = complete disgrace or ostracism
--   0.5 = neutral or unknown (default starting value)
--   1.0 = exceptional standing, full acceptance
--
-- Tracked primarily for the player character. May also be seeded for NPCs
-- whose faction standing affects adjudication — e.g. Wickham's standing with
-- the militia regiment affects what other characters will say about him in
-- Pass 2 context.
--
-- Pass 2 updates these via 'faction_reputation_changes' in outcome JSON:
--   [{"character_id": N, "faction_id": M, "delta": -0.08,
--     "reason": "Elizabeth refused to manage Mrs. Bennet's outburst"}]
-- The engine applies delta and clamps to [0.0, 1.0] in _apply_outcome().
-- The reason string is written to the notes field on the same row.
--
-- Rows may be added mid-play when new factions form or when a character
-- first becomes relevant to a faction that was previously out of scope.
CREATE TABLE character_faction_reputation (
    character_id    INTEGER NOT NULL REFERENCES character(id),
    faction_id      INTEGER NOT NULL REFERENCES faction(id),

    -- Standing value: 0.0 (ostracised) to 1.0 (full acceptance). 0.5 = neutral.
    reputation      REAL    NOT NULL DEFAULT 0.5
        CHECK(reputation BETWEEN 0.0 AND 1.0),

    -- Human-readable note on why standing is at its current value.
    -- Set by seed; updated by Pass 2 alongside each delta. Included in the
    -- faction_reputations block of the Pass 2 context packet so the LLM has
    -- narrative context for reputation decisions, not just a float.
    -- Example: "Bennet family pleased with her conduct; no embarrassments yet"
    notes           TEXT,

    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    PRIMARY KEY (character_id, faction_id)
);

CREATE INDEX idx_faction_rep_character ON character_faction_reputation(character_id);


-- -----------------------------------------------------------------------------
-- 3. location_connection: passage_note
-- -----------------------------------------------------------------------------

-- Natural language description of the barrier type on this connection.
-- Provides Pass 2 with the semantic context needed to adjudicate what
-- happens when a character attempts to pass a non-open connection.
--
-- The is_passable flag remains the engine's binary movement gate: 0 means
-- the engine will not route the player through this connection regardless
-- of LLM output. passage_note is advisory context for the LLM only.
--
-- The critical distinction this field enables:
--   'locked' — physically impassable; a key or forced entry is required.
--              Pass 2 should refuse movement and adjudicate the attempt.
--   'closed by convention' — door is unlocked but social norms prohibit
--              entry. Pass 2 should adjudicate the reputational cost rather
--              than refusing outright. A sufficiently motivated or oblivious
--              character can enter; the consequence is social, not physical.
--
-- NULL = no special note; connection type and is_passable are sufficient.
--
-- Meryton assembly examples:
--   Supper room door: 'Closed by convention — door unlocked, room unlit and
--     unused. Entering would be considered improper without compelling reason.'
--   Corn market passage: 'Locked during the evening assembly.'
ALTER TABLE location_connection
    ADD COLUMN passage_note TEXT DEFAULT NULL;


-- -----------------------------------------------------------------------------
-- 4. character: pending_intent
-- -----------------------------------------------------------------------------

-- A working-memory slot for deferred social obligations and queued intentions.
-- Stores a natural language string describing what this character intends to
-- do, or is socially obligated to do, as a result of a prior interaction.
--
-- Set and cleared by Pass 2 via 'pending_intent_updates' in outcome JSON:
--   [{"character_id": N, "intent": "owes reciprocal grooming to Toulouse"}]
-- An empty string or explicit null clears the field (obligation discharged).
--
-- Included in the NPC profile block of the Pass 2 context packet, so the LLM
-- reads the obligation when adjudicating subsequent turns. This makes social
-- commitments durable across turn boundaries without requiring the LLM to
-- recall them from action log history.
--
-- Applicable to: reciprocal social gestures, dance card commitments, promises
-- made in prior turns, and hidden agendas a character is actively pursuing
-- (e.g. Wickham's concealed financial motivations toward the Bennet family).
--
-- Distinct from:
--   emotional_state  — short-term mood; qualitative label
--   internal_state   — quantitative physiological floats with passive rates
--   character_goal   — stable motivational weights (Ford-Nichols taxonomy)
-- This field is a short-term behavioral commitment, not a stable trait.
ALTER TABLE character
    ADD COLUMN pending_intent TEXT DEFAULT NULL;


-- -----------------------------------------------------------------------------
-- Schema version
-- -----------------------------------------------------------------------------

INSERT INTO schema_version (version, description)
VALUES (7, 'Add faction and character_faction_reputation tables; add passage_note to location_connection; add pending_intent to character');
