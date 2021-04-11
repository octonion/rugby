begin;

drop table if exists varsity.games;

set datestyle to 'SQL, DMY';

create table varsity.games (
	season			integer,
	home_team		text,
	home_score		integer,
	away_score		integer,
	away_team		text,
	date			date,
	stadium			text
);

copy varsity.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table varsity.games add column game_id serial;

commit;
