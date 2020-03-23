#!/bin/bash

cmd="psql template1 --tuples-only --command \"select count(*) from pg_database where datname = 'rugby';\""

db_exists=`eval $cmd`
 
if [ $db_exists -eq 0 ] ; then
   cmd="createdb rugby;"
   eval $cmd
fi

psql rugby -f schema/create_schema.sql

cat csv/games_*.csv >> /tmp/games.csv
psql rugby -f loaders/load_games.sql
rm /tmp/games.csv
