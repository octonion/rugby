begin;

drop table if exists sr.games;

create table sr.games (
	date			date,
	home_team		text,
	away_team		text,
	home_score		integer,
	away_score		integer,
	play_off_game		boolean,
	op_home_odds		numeric(10,2),
	op_draw_odds		numeric(10,2),
	op_away_odds		numeric(10,2),
	op_bookmakers_surveyed	integer,
	home_odds_open		numeric(10,2),
	home_odds_min		numeric(10,2),
	home_odds_max		numeric(10,2),
	home_odds_close		numeric(10,2),
	away_odds_open		numeric(10,2),
	away_odds_min		numeric(10,2),
	away_odds_max		numeric(10,2),
	away_odds_close		numeric(10,2),
	home_line_open		numeric(10,2),
	home_line_min		numeric(10,2),
	home_line_max		numeric(10,2),
	home_line_close		numeric(10,2),
	away_line_open		numeric(10,2),
	away_line_min		numeric(10,2),
	away_line_max		numeric(10,2),
	away_line_close		numeric(10,2),
	home_line_odds_open	numeric(10,2),
	home_line_odds_min	numeric(10,2),
	home_line_odds_max	numeric(10,2),
	home_line_odds_close	numeric(10,2),
	away_line_odds_open	numeric(10,2),
	away_line_odds_min	numeric(10,2),
	away_line_odds_max	numeric(10,2),
	away_line_odds_close	numeric(10,2),
	total_score_open	numeric(10,2),
	total_score_min		numeric(10,2),
	total_score_max		numeric(10,2),
	total_score_close	numeric(10,2),
	total_score_over_open	numeric(10,2),
	total_score_over_min	numeric(10,2),
	total_score_over_max	numeric(10,2),
	total_score_over_close	numeric(10,2),
	total_score_under_open	numeric(10,2),
	total_score_under_min	numeric(10,2),
	total_score_under_max	numeric(10,2),
	total_score_under_close	numeric(10,2),
	notes			text
);

copy sr.games from '/tmp/games.csv' with delimiter as ',' csv quote as '"' header;

alter table sr.games add column game_id serial;

commit;
