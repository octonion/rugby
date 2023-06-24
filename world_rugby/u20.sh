#!/bin/bash

psql rugby -c "drop table if exists u20.results;"

psql rugby -f u20/standardized_results.sql

psql rugby -c "vacuum full verbose analyze u20.results;"

psql rugby -c "drop table if exists u20._basic_factors;"
psql rugby -c "drop table if exists u20._parameter_levels;"

R -f u20/lmer.R

psql rugby -c "vacuum full verbose analyze u20._parameter_levels;"
psql rugby -c "vacuum full verbose analyze u20._basic_factors;"

psql rugby -f u20/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze u20._factors;"

psql rugby -f u20/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze u20._schedule_factors;"

psql rugby -f u20/current_ranking.sql > u20/current_ranking.txt
cp /tmp/current_ranking.csv u20/current_ranking.csv

psql rugby -f u20/predict_monthly.sql > u20/predict_monthly.txt
cp /tmp/predict_monthly.csv u20/predict_monthly.csv

psql rugby -f u20/predict.sql > u20/predict.txt
cp /tmp/predict.csv u20/predict.csv
