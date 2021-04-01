begin;

select

sf1.team_id as home,
sf2.team_id as away,
(exp(i.estimate)*sf1.offensive*o.exp_factor*sf2.defensive)::numeric(4,1) as e_home,
(exp(i.estimate)*sf2.offensive*d.exp_factor*sf1.defensive)::numeric(4,1) as e_away,
((exp(i.estimate)*sf1.offensive*o.exp_factor*sf2.defensive)-
(exp(i.estimate)*sf2.offensive*d.exp_factor*sf1.defensive))::numeric(4,1) as e_d

from sl._schedule_factors sf1, sl._schedule_factors sf2

join sl._factors o
  on (o.parameter,o.level)=('field','offense_home')
join sl._factors d
  on (d.parameter,d.level)=('field','defense_home')

join sl._basic_factors i
  on (i.factor)=('(Intercept)')

where
    (sf1.team_id,sf2.team_id) in
(
('Sharks','Lions')
);
