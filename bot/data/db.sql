-- Script to initialize postgreSQL bot database

-- ACHIEVEMENT FEATURE --
-------------------------
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
CREATE INDEX IF NOT EXISTS achievement_progress_discord_id_idx ON achievement_progress (discord_id);
CREATE INDEX IF NOT EXISTS achievement_progress_achievement_id_idx ON achievement_progress (achievement_id);


CREATE TABLE achievement_leaderboard(
	discord_id BIGINT NOT NULL,
	total_completed INT DEFAULT 0,
	FOREIGN KEY(discord_id) REFERENCES warnet_user(discord_id),
	UNIQUE(discord_id)
);
CREATE INDEX IF NOT EXISTS achievement_leaderboard_discord_id_idx ON achievement_leaderboard (discord_id);


CREATE OR REPLACE FUNCTION insert_user_to_leaderboard() RETURNS trigger AS
$$
	BEGIN
		INSERT INTO achievement_leaderboard VALUES(NEW.discord_id);
		RETURN NEW;
	END;
$$
LANGUAGE plpgsql;


CREATE TRIGGER trigger_insert_user_to_leaderboard
AFTER INSERT ON warnet_user 
FOR EACH ROW
EXECUTE PROCEDURE insert_user_to_leaderboard();


CREATE OR REPLACE FUNCTION update_total_completed_achievement() RETURNS trigger AS
$$
	BEGIN
		if (TG_OP = 'INSERT') THEN
			UPDATE achievement_leaderboard
			SET total_completed = total_completed + 1
			WHERE discord_id = NEW.discord_id;
			RETURN NEW;
		ELSIF (TG_OP = 'DELETE') THEN
			UPDATE achievement_leaderboard
			SET total_completed = total_completed - 1
			WHERE discord_id = OLD.discord_id;
			RETURN NEW;
		END IF;
	END;
$$
LANGUAGE plpgsql;


CREATE TRIGGER trigger_update_total_completed_achievement
AFTER INSERT OR DELETE ON achievement_progress 
FOR EACH ROW
EXECUTE PROCEDURE update_total_completed_achievement();


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


-- WARN AND MUTE FEATURE --
---------------------------
CREATE TABLE warned_members(
	discord_id BIGINT NOT NULL,
	warn_level INT DEFAULT 1 NOT NULL,
	date_given TIMESTAMP DEFAULT NOW() NOT NULL,
	date_expire TIMESTAMP NOT NULL,
	reason VARCHAR(256),
	leave_server BOOLEAN DEFAULT '0' NOT NULL,
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
	leave_server BOOLEAN DEFAULT '0' NOT NULL,
	roles_store BIGINT[],
	PRIMARY KEY(discord_id),
	UNIQUE(discord_id)
);
CREATE INDEX IF NOT EXISTS muted_members_discord_id_idx ON muted_members (discord_id);