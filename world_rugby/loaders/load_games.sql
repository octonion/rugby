begin;

drop table if exists wr.games;

create table wr.games (
	match_id	      integer,
	description	      text,
        venue_id	      integer,
	venue_name	      text,
	venue_city	      text,
	venue_country	      text,
        time_millis	      text,
	time_gmtoffset	      text,
	time_label	      timestamp,
	attendance	      integer,
        team_id		      integer,
	team_name	      text,
	team_abbr	      text,
	opponent_id	      integer,
	opponent_name	      text,
	opponent_abbr	      text,
	team_score	      integer,
	opponent_score	      integer,
	status		      text,
	outcome		      text,
	events_id	      integer,
	events_label	      text,
	events_sport	      text,
        events_start_millis   text,
	events_start_label    text,
        events_end_millis     text,
	events_end_label      text,
        match_json	      json,
	primary key (match_id)
);

copy wr.games from '/tmp/games.csv' with delimiter as ',' csv quote as '"';

--alter table wr.games add column game_id serial;

commit;
