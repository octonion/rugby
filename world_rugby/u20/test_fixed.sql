select npl.parameter,npl.type,npl.level,nbf.estimate
from u20._parameter_levels npl
left outer join u20._basic_factors nbf
  on (nbf.factor,nbf.type)=(npl.parameter||npl.level,npl.type)
where npl.type='fixed'
order by parameter,level;
