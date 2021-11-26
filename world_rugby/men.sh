#!/bin/bash

psql rugby -c "drop table if exists men.results;"

psql rugby -f men/standardized_results.sql

psql rugby -c "vacuum full verbose analyze men.results;"

psql rugby -c "drop table if exists men._basic_factors;"
psql rugby -c "drop table if exists men._parameter_levels;"

R --vanilla -f men/lmer.R

psql rugby -c "vacuum full verbose analyze men._parameter_levels;"
psql rugby -c "vacuum full verbose analyze men._basic_factors;"

psql rugby -f men/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze men._factors;"

psql rugby -f men/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze men._schedule_factors;"

psql rugby -f men/current_ranking.sql > men/current_ranking.txt
cp /tmp/current_ranking.csv men/current_ranking.csv

psql rugby -f men/predict_monthly.sql > men/predict_monthly.txt
cp /tmp/predict_monthly.csv men/predict_monthly.csv

psql rugby -f men/predict.sql > men/predict.txt
cp /tmp/predict.csv men/predict.csv
