-- seed_v7.sql — I Am a Cat module
-- Corrects wander_probability for Guy (id=4) and Mama (id=3).
--
-- Reason: seed_v3.sql set these values near-zero (0.05 and 0.03 respectively)
-- as a proxy for missing sleepiness suppression. The suppression mechanism was
-- implemented in schema v7 / engine v7: the NPC wander roll is skipped whenever
-- a character's sleepiness internal_state >= WANDER_SLEEPINESS_THRESHOLD (0.60,
-- default). With that gate in place, honest base probabilities are safe.
--
-- Guy (sleepiness 0.88 at start): suppressed for ~47 game-minutes until sleepiness
-- drops below 0.60 (natural wakeup ~5:27 AM). Base value of 0.20 reflects a
-- human who is restless or approaching wakeup — roughly one autonomous move
-- per 5 turns once suppression lifts.
--
-- Mama (sleepiness 0.22 at start): already below the suppression threshold; her
-- wander_probability is live from turn one. Value of 0.10 reflects a light sleeper
-- who may get up once or twice during the session — roughly one move per 10 turns.
-- This is consistent with the "lightly_asleep" emotional state and the note in
-- implementation_status.md that she realistically gets up for the bathroom at night.
--
-- Attribution: developed with the assistance of Claude (claude-sonnet-4-6, Anthropic).

UPDATE character
SET wander_probability = 0.20
WHERE id = 4;  -- Guy

UPDATE character
SET wander_probability = 0.10
WHERE id = 3;  -- Mama
