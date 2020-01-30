#!/bin/bash

psql rugby -c "drop table if exists wr.men_results;"

psql rugby -f men/standardized_results.sql

psql rugby -c "vacuum full verbose analyze wr.men_results;"

psql rugby -c "drop table if exists wr._men_basic_factors;"
psql rugby -c "drop table if exists wr._men_parameter_levels;"

R --vanilla -f men/lmer.R

psql rugby -c "vacuum full verbose analyze wr._men_parameter_levels;"
psql rugby -c "vacuum full verbose analyze wr._men_basic_factors;"

psql rugby -f men/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze wr._men_factors;"

psql rugby -f men/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze wr._men_schedule_factors;"

psql rugby -f men/current_ranking.sql > men/current_ranking.txt
cp /tmp/current_ranking.csv men/current_ranking.csv

psql rugby -f men/predict_monthly.sql > men/predict_monthly.txt
cp /tmp/predict_monthly.csv men/predict_monthly.csv

psql rugby -f men/predict.sql > men/predict.txt
cp /tmp/predict.csv men/predict.csv
