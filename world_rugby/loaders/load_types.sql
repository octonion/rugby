begin;

drop table if exists world_rugby.types;

create table world_rugby.types (
	type_id	      integer,
	type_name     text,
	primary key (type_id)
);

copy world_rugby.types from '/tmp/types.csv' with delimiter as ',' csv quote as '"';

commit;
