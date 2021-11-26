#!/bin/bash

psql rugby -c "drop table if exists women.results;"

psql rugby -f women/standardized_results.sql

psql rugby -c "vacuum full verbose analyze women.results;"

psql rugby -c "drop table if exists women._basic_factors;"
psql rugby -c "drop table if exists women._parameter_levels;"

R --vanilla -f women/lmer.R

psql rugby -c "vacuum full verbose analyze women._parameter_levels;"
psql rugby -c "vacuum full verbose analyze women._basic_factors;"

psql rugby -f women/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze women._factors;"

psql rugby -f women/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze women._schedule_factors;"

psql rugby -f women/current_ranking.sql > women/current_ranking.txt
cp /tmp/current_ranking.csv women/current_ranking.csv

psql rugby -f women/predict_monthly.sql > women/predict_monthly.txt
cp /tmp/predict_monthly.csv women/predict_monthly.csv

psql rugby -f women/predict.sql > women/predict.txt
cp /tmp/predict.csv women/predict.csv
