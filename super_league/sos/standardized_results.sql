begin;

drop table if exists sl.results;

create table sl.results (
	game_id		      integer,
	year		      integer,
--	game_date	      date,
	team_name	      text,
	opponent_name	      text,
	field		      text,
	team_score	      integer,
	opponent_score	      integer

);

insert into sl.results
(game_id,
 year,
-- game_date,
 team_name,
 opponent_name,
 field,
 team_score,
 opponent_score)
(
select
game_id,
year,
--date,
home_team,
away_team,
'offense_home',
home_score,
away_score

from sl.games

where
    year between 2003 and 2021

and home_score is not null
and away_score is not null

--and not(home_score,away_score)=(0,0)
);

insert into sl.results
(game_id,
 year,
-- game_date,
 team_name,
 opponent_name,
 field,
 team_score,
 opponent_score)
(
select
game_id,
year,
--date,
away_team,
home_team,
'defense_home',
away_score,
home_score

from sl.games

where
    year between 2003 and 2021

and home_score is not null
and away_score is not null

--and not(home_score,away_score)=(0,0)
);

commit;
