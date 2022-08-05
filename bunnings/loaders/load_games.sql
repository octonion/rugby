begin;

drop table if exists bunnings.games;

set datestyle to 'SQL, DMY';

create table bunnings.games (
	season			integer,
	date			timestamp,
	home_team		text,
	away_team		text,
	home_score		integer,
	away_score		integer,
	home_1h			integer,
	away_1h			integer,
	home_2h			integer,
	away_2h			integer,
	home_aet		integer,
	away_aet		integer,
	aet			text
);

copy bunnings.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table bunnings.games add column game_id serial;

commit;
