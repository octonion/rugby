#!/bin/bash

psql rugby -c "drop table if exists wr.results;"

psql rugby -f sos/standardized_results.sql

psql rugby -c "vacuum full verbose analyze wr.results;"

psql rugby -c "drop table if exists wr._zinb_basic_factors;"
psql rugby -c "drop table if exists wr._zinb_parameter_levels;"

R --vanilla -f sos/zinb.R

psql rugby -c "vacuum full verbose analyze wr._zinb_parameter_levels;"
psql rugby -c "vacuum full verbose analyze wr._zinb_basic_factors;"

psql rugby -f sos/zinb_normalize_factors.sql
psql rugby -c "vacuum full verbose analyze wr._zinb_factors;"

psql rugby -f sos/zinb_schedule_factors.sql
psql rugby -c "vacuum full verbose analyze wr._zinb_schedule_factors;"

psql rugby -f sos/zinb_current_ranking.sql > sos/zinb_current_ranking.txt
cp /tmp/zinb_current_ranking.csv sos/zinb_current_ranking.csv
