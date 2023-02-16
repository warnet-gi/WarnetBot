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
