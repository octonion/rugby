#!/bin/bash

psql rugby -c "drop table if exists major_league.results;"

psql rugby -f sos/standardized_results.sql

psql rugby -c "vacuum full verbose analyze major_league.results;"

psql rugby -c "drop table if exists major_league._basic_factors;"
psql rugby -c "drop table if exists major_league._parameter_levels;"

R --vanilla -f sos/lmer.R

psql rugby -c "vacuum full verbose analyze major_league._parameter_levels;"
psql rugby -c "vacuum full verbose analyze major_league._basic_factors;"

psql rugby -f sos/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze major_league._factors;"

psql rugby -f sos/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze major_league._schedule_factors;"

psql rugby -f sos/current_ranking.sql > sos/current_ranking.txt
cp /tmp/current_ranking.csv sos/current_ranking.csv

psql rugby -f sos/predictions.sql > sos/predictions.txt
cp /tmp/predictions.csv sos/predictions.csv
