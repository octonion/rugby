#!/bin/bash

cmd="psql template1 --tuples-only --command \"select count(*) from pg_database where datname = 'rugby';\""

db_exists=`eval $cmd`
 
if [ $db_exists -eq 0 ] ; then
   cmd="createdb rugby;"
   eval $cmd
fi

psql rugby -f schema/create_schema.sql

cp csv/sports.csv /tmp/sports.csv
psql rugby -f loaders/load_sports.sql
rm /tmp/sports.csv

cp csv/types.csv /tmp/types.csv
psql rugby -f loaders/load_types.sql
rm /tmp/types.csv

cp csv/countries.csv /tmp/countries.csv
psql rugby -f loaders/load_countries.sql
rm /tmp/countries.csv

cat csv/matches_*.csv >> /tmp/games.csv
psql rugby -f loaders/load_games.sql
rm /tmp/games.csv

psql rugby -f schema/create_teams.sql
