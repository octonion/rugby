begin;

drop table if exists m10.games;

set datestyle to 'SQL, DMY';

create table m10.games (
    match_number    text,
    round_number    text,
	date			timestamp,
	location		text,
	home_team		text,
	away_team		text,
	section			text,
	result			text,
	home_score		integer,
	away_score		integer
);

copy m10.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table m10.games add column game_id serial;

update m10.games
set home_score = split_part(result,' - ',1)::integer,
    away_score = split_part(result,' - ',2)::integer;

commit;
