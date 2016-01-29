select
g2.time_label::date as date,
(g2.time_label::date-g1.time_label::date) as rest,
(case when g1.team_name=g2.team_name then g1.team_name
     when g1.team_name=g2.opponent_name then g1.team_name
     else g1.opponent_name
end) as team
from wr.games g1
join wr.games g2
  on ((g2.team_name in (g1.team_name,g1.opponent_name)) or
      (g2.opponent_name in (g1.team_name,g1.opponent_name)))
where
    extract(year from g1.time_label)=2015
and extract(year from g2.time_label)=2015
and (g2.time_label::date-g1.time_label::date)<5
and (g2.time_label::date-g1.time_label::date)>0
and g1.events_label='Rugby World Cup 2015'
order by g1.time_label::date desc;

select
g2.time_label::date as date,
(g2.time_label::date-g1.time_label::date) as rest,
(case when g1.team_name=g2.team_name then g1.team_name
     when g1.team_name=g2.opponent_name then g1.team_name
     else g1.opponent_name
end) as team
from wr.games g1
join wr.games g2
  on ((g2.team_name in (g1.team_name,g1.opponent_name)) or
      (g2.opponent_name in (g1.team_name,g1.opponent_name)))
where
--    extract(year from g1.time_label)=2015
--and extract(year from g2.time_label)=2015
TRUE
and (g2.time_label::date-g1.time_label::date)<5
and (g2.time_label::date-g1.time_label::date)>0
and g1.events_label like 'Rugby World Cup%'
order by g1.time_label::date desc;
