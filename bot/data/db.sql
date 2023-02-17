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
CREATE TABLE sticky (
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    message text NOT NULL,
    PRIMARY KEY(channel_id),
    UNIQUE(channel_id),
    UNIQUE(message_id)
);
CREATE INDEX IF NOT EXISTS sticky_channel_id_idx ON sticky (channel_id);