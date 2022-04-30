#!/bin/bash

psql rugby -c "drop table if exists club.results;"

psql rugby -f sos/standardized_results.sql

psql rugby -c "vacuum full verbose analyze club.results;"

psql rugby -c "drop table if exists club._zinb_basic_factors;"
psql rugby -c "drop table if exists club._zinb_parameter_levels;"

#R -f sos/zinb.R
R -f sos/zinb.R

psql rugby -c "vacuum full verbose analyze club._zinb_parameter_levels;"
psql rugby -c "vacuum full verbose analyze club._zinb_basic_factors;"

psql rugby -f sos/zinb_normalize_factors.sql
psql rugby -c "vacuum full verbose analyze club._zinb_factors;"

psql rugby -f sos/zinb_schedule_factors.sql
psql rugby -c "vacuum full verbose analyze club._zinb_schedule_factors;"

psql rugby -f sos/zinb_current_ranking.sql > sos/zinb_current_ranking.txt
cp /tmp/zinb_current_ranking.csv sos/zinb_current_ranking.csv

psql rugby -f sos/zinb_predict_monthly.sql > sos/zinb_predict_monthly.txt
cp /tmp/zinb_predict_monthly.csv sos/zinb_predict_monthly.csv

psql rugby -f sos/zinb_predict.sql > sos/zinb_predict.txt
cp /tmp/zinb_predict.csv sos/zinb_predict.csv
