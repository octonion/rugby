begin;

drop table if exists club._schedule_factors;

create table club._schedule_factors (
	team_id			text,
        offensive               float,
        defensive		float,
        strength                float,
        schedule_offensive      float,
        schedule_defensive      float,
        schedule_strength       float,
        schedule_offensive_all	float,
        schedule_defensive_all	float,
        primary key (team_id)
);

-- defensive
-- offensive
-- strength 
-- schedule_offensive
-- schedule_defensive
-- schedule_strength 

insert into club._schedule_factors
(team_id,offensive,defensive)
(
select o.level,o.exp_factor,d.exp_factor
from club._factors o
left outer join club._factors d
  on (d.level,d.parameter)=(o.level,'defense')
where o.parameter='offense'
);

update club._schedule_factors
set strength=offensive/defensive;

----

create temporary table r (
         team_id		text,
         opponent_id		text,
	 field_id		text,
         offensive              float,
         defensive		float,
         strength               float,
	 field			float
);

insert into r
(team_id,opponent_id,field_id)
(
select
r.team_name,
r.opponent_name,
r.field
from club.results r
where r.year between 2012 and 2023
);

update r
set
offensive=o.offensive,
defensive=o.defensive,
strength=o.strength
from club._schedule_factors o
where (r.opponent_id)=(o.team_id);

-- field

update r
set field=f.exp_factor
from club._factors f
where (f.parameter,f.level)=('field',r.field_id);

create temporary table rs (
         team_id		text,
         offensive              float,
         defensive              float,
         strength               float,
         offensive_all		float,
         defensive_all		float
);

insert into rs
(team_id,
 offensive,defensive,strength,offensive_all,defensive_all)
(
select
team_id,
exp(avg(ln(offensive))),
exp(avg(ln(defensive))),
exp(avg(ln(strength))),
exp(avg(ln(offensive/field))),
exp(avg(ln(defensive*field)))
from r
group by team_id
);

update club._schedule_factors
set
  schedule_offensive=rs.offensive,
  schedule_defensive=rs.defensive,
  schedule_strength=rs.strength,
  schedule_offensive_all=rs.offensive_all,
  schedule_defensive_all=rs.defensive_all
from rs
where
  (_schedule_factors.team_id)=(rs.team_id);

commit;
