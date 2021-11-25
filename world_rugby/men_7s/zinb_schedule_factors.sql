begin;

drop table if exists men_7s._zinb_schedule_factors;

create table men_7s._zinb_schedule_factors (
	team_id			integer,
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

insert into men_7s._zinb_schedule_factors
(team_id,offensive,defensive)
(
select o.level::integer,o.exp_factor,d.exp_factor
from men_7s._zinb_factors o
left outer join men_7s._zinb_factors d
  on (d.level,d.parameter)=(o.level,'defense')
where o.parameter='offense'
);

update men_7s._zinb_schedule_factors
set strength=offensive/defensive;

----

create temporary table r (
         team_id		integer,
         opponent_id		integer,
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
r.team_id,
r.opponent_id,
r.field
from men_7s._results r
where r.year between 2012 and 2021
);

update r
set
offensive=o.offensive,
defensive=o.defensive,
strength=o.strength
from men_7s._zinb_schedule_factors o
where (r.opponent_id)=(o.team_id);

-- field

update r
set field=f.exp_factor
from men_7s._zinb_factors f
where (f.parameter,f.level)=('field',r.field_id);

create temporary table rs (
         team_id		integer,
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

update men_7s._zinb_schedule_factors
set
  schedule_offensive=rs.offensive,
  schedule_defensive=rs.defensive,
  schedule_strength=rs.strength,
  schedule_offensive_all=rs.offensive_all,
  schedule_defensive_all=rs.defensive_all
from rs
where
  (_zinb_schedule_factors.team_id)=(rs.team_id);

commit;
