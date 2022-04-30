#!/bin/bash

psql rugby -c "drop table if exists wr.results;"

psql rugby -f women/standardized_results.sql

psql rugby -c "vacuum full verbose analyze wr.results;"

psql rugby -c "drop table if exists wr._zinb_basic_factors;"
psql rugby -c "drop table if exists wr._zinb_parameter_levels;"

R -f women/zinb.R

psql rugby -c "vacuum full verbose analyze wr._zinb_parameter_levels;"
psql rugby -c "vacuum full verbose analyze wr._zinb_basic_factors;"

psql rugby -f women/zinb_normalize_factors.sql
psql rugby -c "vacuum full verbose analyze wr._zinb_factors;"

psql rugby -f women/zinb_schedule_factors.sql
psql rugby -c "vacuum full verbose analyze wr._zinb_schedule_factors;"

psql rugby -f women/zinb_current_ranking.sql > women/zinb_current_ranking.txt
cp /tmp/zinb_current_ranking.csv women/zinb_current_ranking.csv

psql rugby -f women/zinb_predict_monthly.sql > women/zinb_predict_monthly.txt
cp /tmp/zinb_predict_monthly.csv women/zinb_predict_monthly.csv

psql rugby -f women/zinb_predict.sql > women/zinb_predict.txt
cp /tmp/zinb_predict.csv women/zinb_predict.csv
