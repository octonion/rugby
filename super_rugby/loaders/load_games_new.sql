begin;

drop table if exists sr.games;

set datestyle to 'SQL, DMY';

create table sr.games (
	round			text,
	date			timestamp,
	location		text,
	home_team		text,
	away_team		text,
	result			text,
	home_score		integer,
	away_score		integer
);

copy sr.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table sr.games add column game_id serial;

update sr.games
set home_score = split_part(result,' - ',1)::integer,
    away_score = split_part(result,' - ',2)::integer;

commit;
