begin;

drop table if exists sl.games;

create table sl.games (
	year			integer,
	season			text,
	dow			text,
	day			text,
	time			text,
	home_team		text,
	home_score		integer,
	away_team		text,
	away_score		integer,
	referee			text,
	venue			text
);

copy sl.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table sl.games add column game_id serial;

commit;
