begin;

drop table if exists pro14.games;

set datestyle to 'SQL, MDY';

create table pro14.games (
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

copy pro14.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table pro14.games add column game_id serial;

commit;
