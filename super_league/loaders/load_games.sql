begin;

drop table if exists sl.games;

set datestyle to 'SQL, DMY';

create table sl.games (
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

copy sl.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table sl.games add column game_id serial;

commit;
