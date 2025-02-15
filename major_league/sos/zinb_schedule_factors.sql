begin;

drop table if exists major_league._zinb_schedule_factors;

create table major_league._zinb_schedule_factors (
	team_name			text,
        offensive               float,
        defensive		float,
        strength                float,
        schedule_offensive      float,
        schedule_defensive      float,
        schedule_strength       float,
        schedule_offensive_all	float,
        schedule_defensive_all	float,
        primary key (team_name)
);

-- defensive
-- offensive
-- strength 
-- schedule_offensive
-- schedule_defensive
-- schedule_strength 

insert into major_league._zinb_schedule_factors
(team_name,offensive,defensive)
(
select o.level,o.exp_factor,d.exp_factor
from major_league._zinb_factors o
left outer join major_league._zinb_factors d
  on (d.level,d.parameter)=(o.level,'defense')
where o.parameter='offense'
);

update major_league._zinb_schedule_factors
set strength=offensive/defensive;

----

create temporary table r (
         team_name		text,
         opponent_name		text,
	 field_id		text,
         offensive              float,
         defensive		float,
         strength               float,
	 field			float
);

insert into r
(team_name,opponent_name,field_id)
(
select
r.team_name,
r.opponent_name,
r.field
from major_league.results r
where r.year between 2012 and 2025
);

update r
set
offensive=o.offensive,
defensive=o.defensive,
strength=o.strength
from major_league._zinb_schedule_factors o
where (r.opponent_name)=(o.team_name);

-- field

update r
set field=f.exp_factor
from major_league._zinb_factors f
where (f.parameter,f.level)=('field',r.field_id);

create temporary table rs (
         team_name		text,
         offensive              float,
         defensive              float,
         strength               float,
         offensive_all		float,
         defensive_all		float
);

insert into rs
(team_name,
 offensive,defensive,strength,offensive_all,defensive_all)
(
select
team_name,
exp(avg(ln(offensive))),
exp(avg(ln(defensive))),
exp(avg(ln(strength))),
exp(avg(ln(offensive/field))),
exp(avg(ln(defensive*field)))
from r
group by team_name
);

update major_league._zinb_schedule_factors
set
  schedule_offensive=rs.offensive,
  schedule_defensive=rs.defensive,
  schedule_strength=rs.strength,
  schedule_offensive_all=rs.offensive_all,
  schedule_defensive_all=rs.defensive_all
from rs
where
  (_zinb_schedule_factors.team_name)=(rs.team_name);

commit;
