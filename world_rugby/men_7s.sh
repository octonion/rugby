#!/bin/bash

psql rugby -c "drop table if exists men_7s.results;"

psql rugby -f men_7s/standardized_results.sql

psql rugby -c "vacuum full verbose analyze men_7s.results;"

psql rugby -c "drop table if exists men_7s._basic_factors;"
psql rugby -c "drop table if exists men_7s._parameter_levels;"

R -f men_7s/lmer.R

psql rugby -c "vacuum full verbose analyze men_7s._parameter_levels;"
psql rugby -c "vacuum full verbose analyze men_7s._basic_factors;"

psql rugby -f men_7s/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze men_7s._factors;"

psql rugby -f men_7s/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze men_7s._schedule_factors;"

psql rugby -f men_7s/current_ranking.sql > men_7s/current_ranking.txt
cp /tmp/current_ranking.csv men_7s/current_ranking.csv

psql rugby -f men_7s/predict_monthly.sql > men_7s/predict_monthly.txt
cp /tmp/predict_monthly.csv men_7s/predict_monthly.csv

psql rugby -f men_7s/predict.sql > men_7s/predict.txt
cp /tmp/predict.csv men_7s/predict.csv
