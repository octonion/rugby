begin;

drop table if exists ercc.games;

set datestyle to 'SQL, DMY';

create table ercc.games (
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

copy ercc.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table ercc.games add column game_id serial;

commit;
