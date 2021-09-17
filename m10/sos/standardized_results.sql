begin;

drop table if exists m10.results;

create table m10.results (
	game_id		      integer,
	year		      integer,
	game_date	      date,
	team_name	      text,
	opponent_name	      text,
	field		      text,
	team_score	      integer,
	opponent_score	      integer

);

insert into m10.results
(game_id,
 year,
 game_date,
 team_name,
 opponent_name,
 field,
 team_score,
 opponent_score)
(
select
game_id,
extract(year from date),
date,
home_team,
away_team,
'offense_home',
home_score,
away_score

from m10.games

where
    extract(year from date) between 2003 and 2021

and home_score is not null
and away_score is not null

--and not(home_score,away_score)=(0,0)
);

insert into m10.results
(game_id,
 year,
 game_date,
 team_name,
 opponent_name,
 field,
 team_score,
 opponent_score)
(
select
game_id,
extract(year from date),
date,
away_team,
home_team,
'defense_home',
away_score,
home_score

from m10.games

where
    extract(year from date) between 2003 and 2021

and home_score is not null
and away_score is not null

--and not(home_score,away_score)=(0,0)
);

commit;
