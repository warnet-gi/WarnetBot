-- Custom role v2 (booster roles adopted from Solaris-3): ALTER step.
--
-- Run ONCE, before deploying the new bot:    psql "$DATABASE_URL" -f bot/data/migrations/001_custom_role_v2.sql
-- Safe to re-run: it does nothing when `custom_roles` already exists.
-- After deploying, run `war!colorbackfill` in the guild to fill name/colors/guild/wearers from Discord.
--
-- Old: custom_role(role_id, owner_discord_id, created_at)
-- New: custom_roles(role_id, guild_id, owner_id, name, style, primary_color, secondary_color, created_at)
--      custom_role_members(role_id, user_id, joined_at)   -- who currently wears a role
--
-- guild_id and name stay nullable until the backfill runs (it then sets them NOT NULL).
-- Rows with guild_id NULL are invisible to the bot until backfilled.
-- A full copy of the old table is kept in custom_role_backup (drop it when you are happy).

BEGIN;

DO $$
BEGIN
    IF to_regclass('custom_role') IS NOT NULL AND to_regclass('custom_roles') IS NULL THEN
        CREATE TABLE custom_role_backup AS SELECT * FROM custom_role;

        ALTER TABLE custom_role RENAME TO custom_roles;
        ALTER TABLE custom_roles RENAME COLUMN owner_discord_id TO owner_id;
        ALTER TABLE custom_roles
            ADD COLUMN guild_id BIGINT,
            ADD COLUMN name TEXT,
            ADD COLUMN style TEXT NOT NULL DEFAULT 'single',
            ADD COLUMN primary_color TEXT,
            ADD COLUMN secondary_color TEXT;

        -- New rule: one owned role per user. If someone owned several, keep the oldest
        -- and orphan the rest (owner_id NULL: still wearable, only staff can edit/delete).
        -- The original owners are preserved in custom_role_backup.
        UPDATE custom_roles c
        SET owner_id = NULL
        FROM (
            SELECT role_id, ROW_NUMBER() OVER (PARTITION BY owner_id ORDER BY created_at, role_id) AS rn
            FROM custom_roles
            WHERE owner_id IS NOT NULL
        ) d
        WHERE c.role_id = d.role_id AND d.rn > 1;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS custom_roles_guild_owner_uidx ON custom_roles (guild_id, owner_id);
CREATE INDEX IF NOT EXISTS custom_roles_guild_created_idx ON custom_roles (guild_id, created_at, role_id);

CREATE TABLE IF NOT EXISTS custom_role_members (
    role_id BIGINT REFERENCES custom_roles (role_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (role_id, user_id)
);
CREATE INDEX IF NOT EXISTS custom_role_members_user_id_idx ON custom_role_members (user_id);

COMMIT;
