-- Script to initialize postgreSQL bot database

------ TCG FEATURE ------
-------------------------
CREATE TABLE tcg_leaderboard(
	discord_id BIGINT NOT NULL,
	win_count INT DEFAULT 0 NOT NULL,
	loss_count INT DEFAULT 0 NOT NULL,
	elo FLOAT DEFAULT 1500 NOT NULL,
	title BIGINT,
	PRIMARY KEY(discord_id),
	UNIQUE(discord_id)
);
CREATE INDEX IF NOT EXISTS tcg_leaderboard_discord_id_idx ON tcg_leaderboard (discord_id);

----- STICKY FEATURE ----
-------------------------
CREATE TABLE sticky(
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    message text NOT NULL,
    PRIMARY KEY(channel_id),
    UNIQUE(channel_id),
    UNIQUE(message_id)
);
CREATE INDEX IF NOT EXISTS sticky_channel_id_idx ON sticky (channel_id);
CREATE INDEX IF NOT EXISTS sticky_message_id_idx ON sticky (message_id);

----- MESSAGE SCHEDULING FEATURE ----
-------------------------------------
CREATE TABLE scheduled_message(
	id SERIAL NOT NULL,
	guild_id bigint NOT NULL,
	channel_id bigint NOT NULL,
	message text NOT NULL,
	date_trigger TIMESTAMP NOT NULL,
	PRIMARY KEY(id),
	UNIQUE(id)
);
CREATE INDEX IF NOT EXISTS scheduled_message_id_idx ON scheduled_message (id);
CREATE INDEX IF NOT EXISTS scheduled_message_guild_id_idx ON scheduled_message (guild_id);
CREATE INDEX IF NOT EXISTS scheduled_message_channel_id_idx ON scheduled_message (channel_id);

----- BURONAN KHAENRIAH FEATURE ----
------------------------------------
CREATE TABLE buronan_khaenriah(
	discord_id BIGINT NOT NULL,
	warn_level INT NOT NULL DEFAULT 0,
	PRIMARY KEY(discord_id),
	UNIQUE(discord_id)
);
CREATE INDEX IF NOT EXISTS buronan_khaenriah_discord_id_idx ON buronan_khaenriah (discord_id);

---- WARN AND MUTE FEATURE ----
-------------------------------
CREATE TABLE warned_members(
	discord_id BIGINT NOT NULL,
	warn_level INT DEFAULT 1 NOT NULL,
	date_given TIMESTAMP DEFAULT NOW() NOT NULL,
	date_expire TIMESTAMP NOT NULL,
	reason VARCHAR(256),
	leave_server BOOLEAN DEFAULT FALSE NOT NULL,
	PRIMARY KEY(discord_id),
	UNIQUE(discord_id)
);
CREATE INDEX IF NOT EXISTS warned_members_discord_id_idx ON warned_members (discord_id);
CREATE INDEX IF NOT EXISTS warned_members_warn_level_idx ON warned_members (warn_level);

CREATE TABLE muted_members(
	discord_id BIGINT NOT NULL,
	date_given TIMESTAMP DEFAULT NOW() NOT NULL,
	date_expire TIMESTAMP NOT NULL,
	reason VARCHAR(256),
	leave_server BOOLEAN DEFAULT FALSE NOT NULL,
	roles_store BIGINT[],
	PRIMARY KEY(discord_id),
	UNIQUE(discord_id)
);
CREATE INDEX IF NOT EXISTS muted_members_discord_id_idx ON muted_members (discord_id);