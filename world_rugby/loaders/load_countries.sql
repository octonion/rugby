begin;

drop table if exists world_rugby.countries;

create table world_rugby.countries (
	country_id	      integer,
	country_name	      text,
	country_json	      json,
	primary key (country_id)
);

copy world_rugby.countries from '/tmp/countries.csv' with delimiter as ',' csv quote as '"';

commit;
