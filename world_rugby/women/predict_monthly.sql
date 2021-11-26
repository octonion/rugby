begin;

set timezone to 'America/New_York';

select

g.time_label::date as date,

g.events_label as event,
coalesce(g.venue_city,t1.country_name||'?') as city,

(case when g.venue_country=t1.country_name then 'home'
      when g.venue_country=t2.country_name then 'away'
      when g.venue_country is null then 'home'
      else 'neutral' end) as site,

t1.country_name as team,
(
case when g.venue_country=t1.country_name then
       exp(i.estimate)*sf1.offensive*o.exp_factor*sf2.defensive
     when g.venue_country=t2.country_name then
       exp(i.estimate)*sf1.offensive*d.exp_factor*sf2.defensive
     when g.venue_country is null then
       exp(i.estimate)*sf1.offensive*o.exp_factor*sf2.defensive
     else
       exp(i.estimate)*sf1.offensive*sf2.defensive
end
)::numeric(4,1) as e_p,

t2.country_name as opponent,
(
case when g.venue_country=t1.country_name then
       exp(i.estimate)*sf2.offensive*d.exp_factor*sf1.defensive
     when g.venue_country=t2.country_name then
       exp(i.estimate)*sf2.offensive*o.exp_factor*sf1.defensive
     when g.venue_country is null then
       exp(i.estimate)*sf2.offensive*d.exp_factor*sf1.defensive
     else
       exp(i.estimate)*sf2.offensive*sf1.defensive
end
)::numeric(4,1) as e_p

--skellam(exp(i.estimate)*h.offensive*o.exp_factor*v.defensive,
--        exp(i.estimate)*v.offensive*h.defensive*d.exp_factor,
--	'win')::numeric(4,3) as win,

--skellam(exp(i.estimate)*h.offensive*o.exp_factor*v.defensive,
--        exp(i.estimate)*v.offensive*h.defensive*d.exp_factor,
--	'lose')::numeric(4,3) as lose,

--skellam(exp(i.estimate)*h.offensive*o.exp_factor*v.defensive,
--        exp(i.estimate)*v.offensive*h.defensive*d.exp_factor,
--	'tie')::numeric(4,3) as draw

from world_rugby.games g

join world_rugby.teams t1
  on (t1.team_id) = (g.team_id)
join world_rugby.teams t2
  on (t2.team_id) = (g.opponent_id)

join women._schedule_factors sf1
  on (sf1.team_id)=(t1.team_id)
join women._schedule_factors sf2
  on (sf2.team_id)=(t2.team_id)

join women._factors o
  on (o.parameter,o.level)=('field','offense_home')
join women._factors d
  on (d.parameter,d.level)=('field','defense_home')

join women._basic_factors i
  on (i.factor)=('(Intercept)')

where
   g.time_label::date between current_date and current_date+30

and (t1.sport_id,t1.type_id)=(3,6)
and (t2.sport_id,t2.type_id)=(3,6)

and (g.time_label::date) between coalesce(t1.from_label,g.time_label::date) and coalesce(t1.until_label,g.time_label::date)
and (g.time_label::date) between coalesce(t2.from_label,g.time_label::date) and coalesce(t2.until_label,g.time_label::date)

and (g.team_score,g.opponent_score)=(0,0)

order by date,event,team asc;

copy
(
select

g.time_label::date as date,

g.events_label as event,
coalesce(g.venue_city,t1.country_name||'?') as city,

(case when g.venue_country=t1.country_name then 'home'
      when g.venue_country=t2.country_name then 'away'
      when g.venue_country is null then 'home'
      else 'neutral' end) as site,

t1.country_name as team,
(
case when g.venue_country=t1.country_name then
       exp(i.estimate)*sf1.offensive*o.exp_factor*sf2.defensive
     when g.venue_country=t2.country_name then
       exp(i.estimate)*sf1.offensive*d.exp_factor*sf2.defensive
     when g.venue_country is null then
       exp(i.estimate)*sf1.offensive*o.exp_factor*sf2.defensive
     else
       exp(i.estimate)*sf1.offensive*sf2.defensive
end
)::numeric(4,1) as e_p,

t2.country_name as opponent,
(
case when g.venue_country=t1.country_name then
       exp(i.estimate)*sf2.offensive*d.exp_factor*sf1.defensive
     when g.venue_country=t2.country_name then
       exp(i.estimate)*sf2.offensive*o.exp_factor*sf1.defensive
     when g.venue_country is null then
       exp(i.estimate)*sf2.offensive*d.exp_factor*sf1.defensive
     else
       exp(i.estimate)*sf2.offensive*sf1.defensive
end
)::numeric(4,1) as e_p

--skellam(exp(i.estimate)*h.offensive*o.exp_factor*v.defensive,
--        exp(i.estimate)*v.offensive*h.defensive*d.exp_factor,
--	'win')::numeric(4,3) as win,

--skellam(exp(i.estimate)*h.offensive*o.exp_factor*v.defensive,
--        exp(i.estimate)*v.offensive*h.defensive*d.exp_factor,
--	'lose')::numeric(4,3) as lose,

--skellam(exp(i.estimate)*h.offensive*o.exp_factor*v.defensive,
--        exp(i.estimate)*v.offensive*h.defensive*d.exp_factor,
--	'tie')::numeric(4,3) as draw

from world_rugby.games g

join world_rugby.teams t1
  on (t1.team_id) = (g.team_id)
join world_rugby.teams t2
  on (t2.team_id) = (g.opponent_id)

join women._schedule_factors sf1
  on (sf1.team_id)=(t1.team_id)
join women._schedule_factors sf2
  on (sf2.team_id)=(t2.team_id)

join women._factors o
  on (o.parameter,o.level)=('field','offense_home')
join women._factors d
  on (d.parameter,d.level)=('field','defense_home')

join women._basic_factors i
  on (i.factor)=('(Intercept)')

where
   g.time_label::date between current_date and current_date+30

and (t1.sport_id,t1.type_id)=(3,6)
and (t2.sport_id,t2.type_id)=(3,6)

and (g.time_label::date) between coalesce(t1.from_label,g.time_label::date) and coalesce(t1.until_label,g.time_label::date)
and (g.time_label::date) between coalesce(t2.from_label,g.time_label::date) and coalesce(t2.until_label,g.time_label::date)

and (g.team_score,g.opponent_score)=(0,0)

order by date,event,team asc
) to '/tmp/predict_monthly.csv' csv header;

commit;
