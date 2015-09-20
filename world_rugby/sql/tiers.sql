begin;

create temporary table tiers (
       team 	 text,
       team_id	 integer,
       tier_id	 integer
);

insert into tiers
(team,team_id,tier_id)
values
('Argentina',40,1),
('Australia',38,1),
('England',34,1),
('France',42,1),
('Ireland',36,1),
('Italy',41,1),
('New Zealand',37,1),
('Scotland',35,1),
('South Africa',39,1),
('Wales',33,1);

insert into tiers
(team,team_id,tier_id)
values
('Canada',50,2),
('Fiji',46,2),
('Georgia',720,2),
('Japan',49,2),
--('Portugal',44,2),
('Romania',52,2),
--('Russia',756,2),
('Samoa',45,2),
--('Spain',43,2),
('Tonga',47,2),
('United States',51,2);
--('Uruguay',68,2)
;

create temporary table r (
       rk	 serial,
       tier_id	 integer,
       i	 float,
       ofs	 float,
       dfs	 float
);

insert into r
(tier_id,i,ofs,dfs)
(
select
t.tier_id,
exp(avg(bf.estimate)) as i,
exp(avg(ln(sf.offensive))) as ofs,
exp(avg(ln(sf.defensive))) as dfs
from wr._schedule_factors sf
join tiers t
  on (t.team_id)=(sf.team_id)
join wr._basic_factors bf
  on bf.factor='(Intercept)'
group by t.tier_id
order by t.tier_id);

/*
select
rk,
tier_id as tier,
i::numeric(5,1),
ofs::numeric(5,1),
dfs::numeric(5,1)
from r
order by rk asc;
*/

select
(t1.i*t1.ofs*t2.dfs)::numeric(5,1) as t1_score,
(t1.i*t2.ofs*t1.dfs)::numeric(5,1) as t2_score
from r t1
join r t2
 on (t1.tier_id,t2.tier_id)=(1,2);

/*
select
row_number() over (order by str desc nulls last) as rk,
team,
str::numeric(4,2),
ofs::numeric(4,2),
dfs::numeric(4,2),
sos::numeric(4,2)
from r
order by rk asc;
*/

commit;
