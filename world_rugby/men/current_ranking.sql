begin;

create temporary table r (
       rk	 serial,
       team 	 text,
       team_id	 integer,
       str	 float,
       ofs	 float,
       dfs	 float,
       sos	 float
);

insert into r
(team,team_id,str,ofs,dfs,sos)
(
select
t.team_name,
t.team_id,
ln(sf.strength) as str,
ln(sf.offensive) as ofs,
ln(sf.defensive) as dfs,
ln(sf.schedule_strength) as sos
from wr._men_schedule_factors sf
left join wr.teams t
  on (t.team_id)=(sf.team_id)
order by str desc);

select
rk,
team,
str::numeric(4,2),
ofs::numeric(4,2),
dfs::numeric(4,2),
sos::numeric(4,2)
from r
order by rk asc;

select
row_number() over (order by str desc nulls last) as rk,
team,
str::numeric(4,2),
ofs::numeric(4,2),
dfs::numeric(4,2),
sos::numeric(4,2)
from r
order by rk asc;

copy (
select
rk,
team,
str::numeric(4,2),
ofs::numeric(4,2),
dfs::numeric(4,2),
sos::numeric(4,2)
from r
order by rk asc
) to '/tmp/current_ranking.csv' csv header;

commit;
