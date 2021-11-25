begin;

drop table if exists women_7s._zinb_factors;

create table women_7s._zinb_factors (
       parameter		text,
       level			text,
       type			text,
       method			text,
       raw_factor		float,
       exp_factor		float,
       factor			float
--       primary key (team_name,type,method)
);

-- this can/should be rewomen_7sitten agnostically
-- do random/fixed separately
-- test for the prescence of '/' using like

-- Random factors

-- defense,offense

insert into women_7s._zinb_factors
(parameter,level,type,method,raw_factor,exp_factor)
(
select
npl.parameter as parameter,
npl.level as level,
npl.type as type,
'ln_regression' as method,
estimate as raw_factor,
null as exp_factor
--exp(estimate) as exp_factor
from women_7s._zinb_parameter_levels npl
left outer join women_7s._zinb_basic_factors nbf
  on (nbf.factor,nbf.level,nbf.type)=(npl.parameter,npl.level,npl.type)
where
    npl.type='random'
and npl.parameter in ('defense','offense')
);

-- other random

insert into women_7s._zinb_factors
(parameter,level,type,method,raw_factor,exp_factor)
(
select
npl.parameter as parameter,
npl.level as level,
npl.type as type,
'ln_regression' as method,
estimate as raw_factor,
null as exp_factor
--exp(estimate) as exp_factor
from women_7s._zinb_parameter_levels npl
left outer join women_7s._zinb_basic_factors nbf
  on (nbf.factor,nbf.level,nbf.type)=(npl.parameter,npl.level,npl.type)
where
    npl.type='random'
and npl.parameter not in ('defense','offense')
);

-- Fixed factors

-- field

insert into women_7s._zinb_factors
(parameter,level,type,method,raw_factor,exp_factor)
(
select
npl.parameter as parameter,
npl.level as level,
npl.type as type,
'ln_regression' as method,
coalesce(estimate,0.0) as raw_factor,
null as exp_factor
--coalesce(exp(estimate),1.0) as exp_factor
from women_7s._zinb_parameter_levels npl
left outer join women_7s._zinb_basic_factors nbf
  on (nbf.factor,nbf.type)=(npl.parameter||npl.level,npl.type)
where
    npl.type='fixed'
and npl.parameter in ('field')
and npl.level not in ('neutral')
);

-- other fixed

insert into women_7s._zinb_factors
(parameter,level,type,method,raw_factor,exp_factor)
(
select
npl.parameter as parameter,
npl.level as level,
npl.type as type,
'ln_regression' as method,
coalesce(estimate,0.0) as raw_factor,
null as exp_factor
--coalesce(exp(estimate),1.0) as exp_factor
from women_7s._zinb_parameter_levels npl
left outer join women_7s._zinb_basic_factors nbf
  on (nbf.factor,nbf.type)=(npl.parameter||npl.level,npl.type)
where
    npl.type='fixed'
and npl.parameter not in ('field')
);

update women_7s._zinb_factors
set exp_factor=exp(raw_factor);

-- 'neutral' park confounded with 'none' field; set factor = 1.0 for field 'none'

insert into women_7s._zinb_factors
(parameter,level,type,method,raw_factor,exp_factor)
values
('field','neutral','fixed','ln_regression',0.0,1.0);

commit;
