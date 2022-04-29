#!/bin/bash

psql rugby -c "drop table if exists sl.results;"

psql rugby -f sos/standardized_results.sql

psql rugby -c "vacuum full verbose analyze sl.results;"

psql rugby -c "drop table if exists sl._basic_factors;"
psql rugby -c "drop table if exists sl._parameter_levels;"

R -f sos/lmer.R

psql rugby -c "vacuum full verbose analyze sl._parameter_levels;"
psql rugby -c "vacuum full verbose analyze sl._basic_factors;"

psql rugby -f sos/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze sl._factors;"

psql rugby -f sos/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze sl._schedule_factors;"

psql rugby -f sos/current_ranking.sql > sos/current_ranking.txt
cp /tmp/current_ranking.csv sos/current_ranking.csv

psql rugby -f sos/predictions.sql > sos/predictions.txt
cp /tmp/predictions.csv sos/predictions.csv
