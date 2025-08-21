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

----- STICKY FEATURE -----
--------------------------
CREATE TABLE sticky(
	channel_id BIGINT NOT NULL,
	message_id BIGINT NOT NULL,
	message TEXT NOT NULL,
	delay_time INT DEFAULT 2 NOT NULL,
	PRIMARY KEY(channel_id),
	UNIQUE(channel_id),
	UNIQUE(message_id)
);
CREATE INDEX IF NOT EXISTS sticky_channel_id_idx ON sticky (channel_id);
CREATE INDEX IF NOT EXISTS sticky_message_id_idx ON sticky (message_id);

----- MESSAGE SCHEDULING FEATURE -----
--------------------------------------
CREATE TABLE scheduled_message(
	id SERIAL NOT NULL,
	guild_id bigint NOT NULL,
	channel_id bigint NOT NULL,
	message text NOT NULL,
	date_trigger TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY(id),
	UNIQUE(id)
);
CREATE INDEX IF NOT EXISTS scheduled_message_id_idx ON scheduled_message (id);
CREATE INDEX IF NOT EXISTS scheduled_message_guild_id_idx ON scheduled_message (guild_id);
CREATE INDEX IF NOT EXISTS scheduled_message_channel_id_idx ON scheduled_message (channel_id);

----- BURONAN KHAENRIAH FEATURE -----
-------------------------------------
CREATE TABLE buronan_khaenriah(
	discord_id BIGINT NOT NULL,
	warn_level INT NOT NULL DEFAULT 0,
	PRIMARY KEY(discord_id),
	UNIQUE(discord_id)
);
CREATE INDEX IF NOT EXISTS buronan_khaenriah_discord_id_idx ON buronan_khaenriah (discord_id);

------- CUSTOM ROLE FEATURE -------
-----------------------------------
CREATE TABLE custom_role(
	role_id BIGINT NOT NULL,
	owner_discord_id BIGINT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
	PRIMARY KEY(role_id),
	UNIQUE(role_id)
);
CREATE INDEX IF NOT EXISTS custom_role_role_id_idx ON custom_role (role_id);

----- TEMPORARY ROLE FEATURE ------
-----------------------------------
CREATE TABLE temp_role (
    id SERIAL NOT NULL,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY(id),
    UNIQUE(user_id, role_id)
);
CREATE INDEX IF NOT EXISTS temp_role_user_role_idx ON temp_role (user_id, role_id);

--- GIVEAWAY BLACKLIST FEATURE ----
-----------------------------------
CREATE TABLE blacklist_ga(
    user_id BIGINT NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
	cooldown_time TIMESTAMP WITH TIME ZONE,
	has_role BOOLEAN DEFAULT TRUE NOT NULL,
	status_user INT NOT NULL, -- 1: in streak phase, 0: not in streak phase 
	PRIMARY KEY(user_id),
	UNIQUE(user_id)
);
CREATE INDEX IF NOT EXISTS blacklist_ga_id_idx ON blacklist_ga (user_id);