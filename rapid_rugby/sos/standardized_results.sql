begin;

drop table if exists rr.results;

create table rr.results (
	game_id		      integer,
	year		      integer,
	game_date	      date,
	team_name	      text,
	opponent_name	      text,
	field		      text,
	team_score	      integer,
	opponent_score	      integer

);

insert into rr.results
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
season,
date,
home_team,
away_team,
'offense_home',
home_score,
away_score

from rr.games

where
    extract(year from date) between 2019 and 2020

and home_score is not null
and away_score is not null
);

insert into rr.results
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
season,
date,
away_team,
home_team,
'defense_home',
away_score,
home_score

from rr.games

where
    extract(year from date) between 2019 and 2020

and home_score is not null
and away_score is not null
);

commit;
