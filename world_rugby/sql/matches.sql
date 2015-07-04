select
--g.opponent_id,
--g.time_label::date,
--g.venue_id,
--g.venue_city,
g.venue_country,
t1.country_name,
--g.team_name,
t2.country_name,
g.outcome,
g.status,
--g.opponent_name
g.team_score,
g.opponent_score
from wr.games g
join wr.teams t1
  on t1.team_id = g.team_id
join wr.teams t2
  on t2.team_id = g.opponent_id
where extract(year from g.time_label)=2014
and (t1.sport_id,t1.type_id)=(1,6)
and (t2.sport_id,t2.type_id)=(1,6)
and (g.time_label::date) between coalesce(t1.from_label,g.time_label::date) and coalesce(t1.until_label,g.time_label::date)
and (g.time_label::date) between coalesce(t2.from_label,g.time_label::date) and coalesce(t2.until_label,g.time_label::date)
and g.team_score is not null
and g.opponent_score is not null
and not(g.team_score,g.opponent_score)=(0,0)
and g.venue_country is null;
--and g.venue_country not in (t1.country_name,t2.country_name);

--and g.venue_id is null
--and g.venue_city is null
--and g.venue_country is null
--and g.team_name='Russia'
--and g.opponent_name='Portugal';

