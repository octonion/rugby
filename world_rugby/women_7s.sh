#!/bin/bash

psql rugby -c "drop table if exists women_7s.results;"

psql rugby -f women_7s/standardized_results.sql

psql rugby -c "vacuum full verbose analyze women_7s.results;"

psql rugby -c "drop table if exists women_7s._basic_factors;"
psql rugby -c "drop table if exists women_7s._parameter_levels;"

R --vanilla -f women_7s/lmer.R

psql rugby -c "vacuum full verbose analyze women_7s._parameter_levels;"
psql rugby -c "vacuum full verbose analyze women_7s._basic_factors;"

psql rugby -f women_7s/normalize_factors.sql
psql rugby -c "vacuum full verbose analyze women_7s._factors;"

psql rugby -f women_7s/schedule_factors.sql
psql rugby -c "vacuum full verbose analyze women_7s._schedule_factors;"

psql rugby -f women_7s/current_ranking.sql > women_7s/current_ranking.txt
cp /tmp/current_ranking.csv women_7s/current_ranking.csv

psql rugby -f women_7s/predict_monthly.sql > women_7s/predict_monthly.txt
cp /tmp/predict_monthly.csv women_7s/predict_monthly.csv

psql rugby -f women_7s/predict.sql > women_7s/predict.txt
cp /tmp/predict.csv women_7s/predict.csv
