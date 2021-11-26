begin;

drop table if exists women._results;

create table women._results (
	game_id		      integer,
	year		      integer,
	game_date	      date,
	country		      text,
	team_name	      text,
	team_id		      integer,
	team_country	      text,
	opponent_name	      text,
	opponent_id	      integer,
	opponent_country      text,
	location_name	      text,
	field		      text,
	team_score	      integer,
	opponent_score	      integer
	--game_length	      text

);

insert into women._results
(game_id,year,
 game_date,
 country,
 team_name,team_id,
 team_country,
 opponent_name,opponent_id,
 opponent_country,
 field,
 team_score,opponent_score)
(
select
g.match_id,
extract(year from g.time_label),
g.time_label::date,

g.venue_country as country,

--t1.country_name,
--t1.country_id,
--t2.country_name,
--t2.country_id,

t1.team_name,
t1.team_id,
t1.country_name,

t2.team_name,
t2.team_id,
t2.country_name,

(case when g.venue_country=t1.country_name then 'offense_home'
      when g.venue_country=t2.country_name then 'defense_home'
      when g.venue_country is null then 'neutral'
      when g.venue_country is null then 'offense_home'
      else 'neutral' end) as field,
g.team_score,
g.opponent_score

from world_rugby.games g
join world_rugby.teams t1
  on t1.team_id = g.team_id
join world_rugby.teams t2
  on t2.team_id = g.opponent_id
where
    extract(year from g.time_label) between 2003 and 2021
    
and t1.sport_id=3
and t2.sport_id=3
and t1.type_id in (6)
and t2.type_id in (6)

and (g.time_label::date) between coalesce(t1.from_label,g.time_label::date) and coalesce(t1.until_label,g.time_label::date)
and (g.time_label::date) between coalesce(t2.from_label,g.time_label::date) and coalesce(t2.until_label,g.time_label::date)

and g.team_score is not null
and g.opponent_score is not null

and not(g.team_score,g.opponent_score)=(0,0)

--and venue_country is not null
);

insert into women._results
(game_id,year,
 game_date,
 country,
 team_name,team_id,
 team_country,
 opponent_name,opponent_id,
 opponent_country,
 field,
 team_score,opponent_score)
(
select
g.match_id,
extract(year from g.time_label),
g.time_label::date,

g.venue_country as country,

t2.team_name,
t2.team_id,
t2.country_name,

t1.team_name,
t1.team_id,
t1.country_name,

--t2.country_name,
--t2.country_id,
--t1.country_name,
--t1.country_id,
(case when g.venue_country=t1.country_name then 'defense_home'
      when g.venue_country=t2.country_name then 'offense_home'
      when g.venue_country is null then 'neutral'
      when g.venue_country is null then 'defense_home'      
      else 'neutral' end) as field,
      
g.opponent_score,
g.team_score

from world_rugby.games g
join world_rugby.teams t1
  on t1.team_id = g.team_id
join world_rugby.teams t2
  on t2.team_id = g.opponent_id
where
    extract(year from g.time_label) between 2003 and 2021
    
--and (t1.sport_id,t1.type_id)=(3,6)
--and (t2.sport_id,t2.type_id)=(3,6)

and t1.sport_id=3
and t2.sport_id=3
and t1.type_id in (6)
and t2.type_id in (6)

and (g.time_label::date) between coalesce(t1.from_label,g.time_label::date) and coalesce(t1.until_label,g.time_label::date)
and (g.time_label::date) between coalesce(t2.from_label,g.time_label::date) and coalesce(t2.until_label,g.time_label::date)

and g.team_score is not null
and g.opponent_score is not null

and not(g.team_score,g.opponent_score)=(0,0)

--and venue_country is not null
);

commit;
