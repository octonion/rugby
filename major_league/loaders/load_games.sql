begin;

drop table if exists major_league.games;

set datestyle to 'SQL, DMY';

create table major_league.games (
	season			integer,
	date			timestamp,
	home_team		text,
	away_team		text,
	home_score		integer,
	away_score		integer,
	home_1h			integer,
	away_1h			integer,
	home_2h			integer,
	away_2h			integer
);

copy major_league.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table major_league.games add column game_id serial;

commit;
