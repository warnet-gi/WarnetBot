-- Script to initialize postgreSQL bot database

CREATE TABLE warnet_user(
	discord_id BIGINT NOT NULL,
	PRIMARY KEY(discord_id),
	UNIQUE(discord_id)
);

CREATE TABLE achievement_progress(
	discord_id BIGINT NOT NULL,
	achievement_id INT NOT NULL,
	completed INT DEFAULT 1 NOT NULL,
	FOREIGN KEY(discord_id) REFERENCES warnet_user(discord_id),
	UNIQUE(discord_id, achievement_id)
);