begin;

drop table if exists rr.games;

create table rr.games (
	date			date,
	season			integer,
	home_team		text,
	home_score		integer,
	away_score		integer,
	away_team		text,
	location		text
);

copy rr.games from '/tmp/games.csv' with delimiter as ',' csv quote as '"';

alter table rr.games add column game_id serial;

commit;
