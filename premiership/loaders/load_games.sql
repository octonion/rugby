begin;

drop table if exists premiership.games;

set datestyle to 'SQL, DMY';

create table premiership.games (
	round			text,
	date			timestamp,
	location		text,
	home_team		text,
	away_team		text,
	result			text,
	home_score		integer,
	away_score		integer
);

copy premiership.games from '/tmp/games.csv' with delimiter as ',' csv;

alter table premiership.games add column game_id serial;

update premiership.games
set home_score = split_part(result,' - ',1)::integer,
    away_score = split_part(result,' - ',2)::integer;

commit;
