begin;

drop table if exists wr.countries;

create table wr.countries (
	country_id	      integer,
	country_name	      text,
	country_json	      json,
	primary key (country_id)
);

copy wr.countries from '/tmp/countries.csv' with delimiter as ',' csv quote as '"';

commit;
