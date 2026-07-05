-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v13 → v14
-- schema/migrations/migrate_v13_to_v14.sql
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Add remote_capability table: can_send_to / can_detect_from
-- -----------------------------------------------------------------------
--
-- Adds the schema for cross-location communication and remote sensing —
-- comm links, telepathy, magical scrying, a spy's remote camera — as an
-- explicit, directional grant between an owner (a character or an item)
-- and a target character, scoped to one sense channel per row.
--
-- Two distinct capabilities, distinguished by consent:
--   'can_send_to'     — the owner actively transmits to the target.
--   'can_detect_from' — the owner passively reads the target regardless of
--                       the target's cooperation (surveillance).
--
-- Directional and one-way per row, matching the existing character_attitude
-- table: a two-way channel between two characters needs two rows, one per
-- direction. Can attach to a character (owner_character_id) or an item
-- (owner_item_id) — exactly one is set, mirroring the loc_id/char_id/item_id
-- pattern already used on the item table (v10). When attached to an item,
-- the effective owner resolves dynamically at query time via whichever
-- character currently holds it (item.char_id) — the capability travels
-- with the item.
--
-- sense is an open natural-language string (no fixed taxonomy), consistent
-- with character_skill.skill_name and the capability_beliefs JSON domains
-- elsewhere in this schema.
--
-- Scope of this migration: schema only. context.py packet assembly and the
-- Pass 1/2/3 prompt rules that consume this table — including the carve-out
-- needed in the existing "NPC presence is authoritative" rule — are a
-- separate, not-yet-implemented follow-on. A table with no rows and no
-- reader is inert; this migration is safe to apply ahead of that work.
--
-- Motivating case: the Suspended demo module (personal, non-public — see
-- modules/suspended_demo/README.md) hand-waved a robot always being
-- co-located with the player to avoid exactly this gap. This table is the
-- real fix; the demo module has not yet been updated to use it.
--
-- Migration notes:
--   Plain CREATE TABLE — no existing table structure changes, no table
--   recreation needed. Per migration rule #2, IF NOT EXISTS is omitted;
--   assumes the DB is at v13.
--
-- Usage:
--   sqlite3 <module>.db < schema/migrations/migrate_v13_to_v14.sql
-- =============================================================================

CREATE TABLE remote_capability (
    id                  INTEGER PRIMARY KEY,

    -- Exactly one of these two identifies who holds this capability.
    owner_character_id  INTEGER REFERENCES character(id),
    owner_item_id       INTEGER REFERENCES item(id),

    -- The character this capability is directed toward.
    target_id           INTEGER NOT NULL REFERENCES character(id),

    -- 'can_send_to'     — owner actively transmits to target (consensual/agentive)
    -- 'can_detect_from' — owner passively reads target regardless of consent
    capability          TEXT    NOT NULL
        CHECK(capability IN ('can_send_to', 'can_detect_from')),

    -- Open natural-language sense/channel label. One row per single sense —
    -- a character sending both dialogue and a sensory feed needs two rows.
    -- Examples: 'words', 'visual_perception', 'tactile_perception',
    -- 'vibration_detection', 'auditory_perception', 'energy_flow_detection',
    -- 'data_interface', 'telepathic_impression'.
    sense                TEXT    NOT NULL,

    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Exactly one owner reference must be set.
    CHECK (
        (owner_character_id IS NOT NULL) +
        (owner_item_id      IS NOT NULL) = 1
    )
);

CREATE INDEX idx_remote_capability_owner_char ON remote_capability(owner_character_id);
CREATE INDEX idx_remote_capability_owner_item ON remote_capability(owner_item_id);
CREATE INDEX idx_remote_capability_target ON remote_capability(target_id);

INSERT INTO schema_version (version, description)
VALUES (14, 'v14: add remote_capability table (can_send_to / can_detect_from) for cross-location communication and remote sensing; schema only, engine integration not yet implemented');
