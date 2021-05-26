begin;

drop table if exists nrl.games;

set datestyle to 'SQL, DMY';

create table nrl.games (
	match_number		text,
	round_number		text,
	date			timestamp,
	location		text,
	home_team		text,
	away_team		text,
	result			text,
	home_score		integer,
	away_score		integer
);

copy nrl.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table nrl.games add column game_id serial;

update nrl.games
set home_score = split_part(result,' - ',1)::integer,
    away_score = split_part(result,' - ',2)::integer;

commit;
