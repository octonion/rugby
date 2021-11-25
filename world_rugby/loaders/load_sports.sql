begin;

drop table if exists world_rugby.sports;

create table world_rugby.sports (
	sport_id	      integer,
	sport_name	      text,
	primary key (sport_id)
);

copy world_rugby.sports from '/tmp/sports.csv' with delimiter as ',' csv quote as '"';

commit;
