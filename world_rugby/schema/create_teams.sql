begin;

drop table if exists wr.teams;

create table wr.teams (
	country_id	      integer,
	country_name	      text,
	team_id		      integer,
	sport_id	      integer,
	type_id		      integer,
	team_name	      text,
	team_abbr	      text,
	from_millis	      text,
	from_label	      date,
	until_millis	      text,
	until_label	      date,
	naming_json	      json
--	team_json	      json
--	primary key (team_id)
);

create temporary table t (
	country_id	      integer,
	country_name	      text,
	team_id		      integer,
	sport_id	      integer,
	type_id		      integer,
	team_name	      text,
	team_abbr	      text,
	names_json	      json,
	team_json	      json
--	primary key (team_id)
);

insert into t
(country_id, country_name, team_json)
--, team_id)
--, sport_id, type_id, team_name,team_abbr)
(select
country_id,
country_name,
json_array_elements(country_json) as team_json
from wr.countries
where json_typeof(country_json)='array'
--, json_array_elements_text(c.country_json) t
);

update t
set team_id = round((team_json->>'id')::real),
    sport_id = round((team_json->>'sport')::real),
    type_id = round((team_json->>'type')::real),
    names_json = (team_json->>'naming')::json;

insert into wr.teams
(country_id, country_name,
 team_id, sport_id, type_id, naming_json)
(
select
country_id,
country_name,
team_id,
sport_id,
type_id,
json_array_elements(names_json) as naming_json
from t
);

update wr.teams
set team_name = coalesce(naming_json->>'name', country_name),
    team_abbr = (naming_json->>'abbr');

update wr.teams
set from_millis = ((naming_json->>'from')::json)->>'millis',
    from_label = (((naming_json->>'from')::json)->>'label')::date
where (naming_json->>'from') is not null;

update wr.teams
set until_millis = ((naming_json->>'until')::json)->>'millis',
    until_label = (((naming_json->>'until')::json)->>'label')::date
where (naming_json->>'until') is not null;

--	from_millis	      text,
--	from_label	      text,
--	until_millis	      text,
--	until_label	      text,

commit;
