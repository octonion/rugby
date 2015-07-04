begin;

drop table if exists wr.sports;

create table wr.sports (
	sport_id	      integer,
	sport_name	      text,
	primary key (sport_id)
);

copy wr.sports from '/tmp/sports.csv' with delimiter as ',' csv quote as '"';

commit;
