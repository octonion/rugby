#!/bin/bash

psql rugby -c "drop table if exists wr.results;"

psql rugby -f men/standardized_results.sql

psql rugby -c "vacuum full verbose analyze wr.results;"

psql rugby -c "drop table if exists wr._men_zinb_basic_factors;"
psql rugby -c "drop table if exists wr._men_zinb_parameter_levels;"

#R --vanilla -f men/zinb.R
R -f men/zinb.R

psql rugby -c "vacuum full verbose analyze wr._men_zinb_parameter_levels;"
psql rugby -c "vacuum full verbose analyze wr._men_zinb_basic_factors;"

psql rugby -f men/zinb_normalize_factors.sql
psql rugby -c "vacuum full verbose analyze wr._men_zinb_factors;"

psql rugby -f men/zinb_schedule_factors.sql
psql rugby -c "vacuum full verbose analyze wr._men_zinb_schedule_factors;"

psql rugby -f men/zinb_current_ranking.sql > men/zinb_current_ranking.txt
cp /tmp/zinb_current_ranking.csv men/zinb_current_ranking.csv

psql rugby -f men/zinb_predict_monthly.sql > men/zinb_predict_monthly.txt
cp /tmp/zinb_predict_monthly.csv men/zinb_predict_monthly.csv

psql rugby -f men/zinb_predict.sql > men/zinb_predict.txt
cp /tmp/zinb_predict.csv men/zinb_predict.csv
