begin;

drop table if exists wr.results;

create table wr.results (
	game_id		      integer,
	year		      integer,
	game_date	      date,
	team_name	      text,
	team_id		      text,
	opponent_name	      text,
	opponent_id	      text,
	location_name	      text,
	field		      text,
	team_score	      integer,
	opponent_score	      integer
	--game_length	      text

);

insert into wr.results
(game_id,year,
 game_date,
 team_name,team_id,
 opponent_name,opponent_id,
 field,
 team_score,opponent_score)
(
select
g.match_id,
extract(year from g.time_label),
g.time_label::date,
t1.country_name,
t1.country_id,
t2.country_name,
t2.country_id,
(case when g.venue_country=t1.country_name then 'offense_home'
      when g.venue_country=t2.country_name then 'defense_home'
      when g.venue_country is null then 'neutral'
      --when g.venue_country is null then 'offense_home'
      else 'neutral' end) as field,
g.team_score,
g.opponent_score

from wr.games g
join wr.teams t1
  on t1.team_id = g.team_id
join wr.teams t2
  on t2.team_id = g.opponent_id
where
    extract(year from g.time_label) between 2008 and 2015
    
and (t1.sport_id,t1.type_id)=(1,6)
and (t2.sport_id,t2.type_id)=(1,6)

and (g.time_label::date) between coalesce(t1.from_label,g.time_label::date) and coalesce(t1.until_label,g.time_label::date)
and (g.time_label::date) between coalesce(t2.from_label,g.time_label::date) and coalesce(t2.until_label,g.time_label::date)

and g.team_score is not null
and g.opponent_score is not null

and not(g.team_score,g.opponent_score)=(0,0)

and venue_country is not null
);

insert into wr.results
(game_id,year,
 game_date,
 team_name,team_id,
 opponent_name,opponent_id,
 field,
 team_score,opponent_score)
(
select
g.match_id,
extract(year from g.time_label),
g.time_label::date,
t2.country_name,
t2.country_id,
t1.country_name,
t1.country_id,
(case when g.venue_country=t1.country_name then 'defense_home'
      when g.venue_country=t2.country_name then 'offense_home'
      when g.venue_country is null then 'neutral'
      --when g.venue_country is null then 'defense_home'      
      else 'neutral' end) as field,
      
g.opponent_score,
g.team_score

from wr.games g
join wr.teams t1
  on t1.team_id = g.team_id
join wr.teams t2
  on t2.team_id = g.opponent_id
where
    extract(year from g.time_label) between 2008 and 2015
    
and (t1.sport_id,t1.type_id)=(1,6)
and (t2.sport_id,t2.type_id)=(1,6)

and (g.time_label::date) between coalesce(t1.from_label,g.time_label::date) and coalesce(t1.until_label,g.time_label::date)
and (g.time_label::date) between coalesce(t2.from_label,g.time_label::date) and coalesce(t2.until_label,g.time_label::date)

and g.team_score is not null
and g.opponent_score is not null

and not(g.team_score,g.opponent_score)=(0,0)

and venue_country is not null
);

commit;