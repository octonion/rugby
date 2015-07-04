begin;

drop table if exists wr.types;

create table wr.types (
	type_id	      integer,
	type_name     text,
	primary key (type_id)
);

copy wr.types from '/tmp/types.csv' with delimiter as ',' csv quote as '"';

commit;
