#!/bin/bash

psql rugby -c "drop table if exists wr.results;"

psql rugby -f rest/standardized_results.sql

psql rugby -c "vacuum full verbose analyze wr.results;"

psql rugby -c "drop table if exists wr._basic_factors;"
psql rugby -c "drop table if exists wr._parameter_levels;"

R --vanilla -f rest/lmer.R

psql rugby -c "vacuum full verbose analyze wr._parameter_levels;"
psql rugby -c "vacuum full verbose analyze wr._basic_factors;"

psql rugby -f rest/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze wr._factors;"

psql rugby -f rest/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze wr._schedule_factors;"

psql rugby -f rest/current_ranking.sql > rest/current_ranking.txt
cp /tmp/current_ranking.csv rest/current_ranking.csv

psql rugby -f rest/predict_monthly.sql > rest/predict_monthly.txt
cp /tmp/predict_monthly.csv rest/predict_monthly.csv

psql rugby -f rest/predict.sql > rest/predict.txt
cp /tmp/predict.csv rest/predict.csv
