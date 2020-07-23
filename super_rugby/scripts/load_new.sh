#!/bin/bash

cmd="psql template1 --tuples-only --command \"select count(*) from pg_database where datname = 'rugby';\""

db_exists=`eval $cmd`
 
if [ $db_exists -eq 0 ] ; then
   cmd="createdb rugby;"
   eval $cmd
fi

psql rugby -f schema/create_schema.sql

mkdir /tmp/data
cp csv/super-rugby-*.csv /tmp/data

dos2unix /tmp/data/*
tail -q -n+2 /tmp/data/*.csv >> /tmp/games.csv
sed -e 's/$/,,/' -i /tmp/games.csv
psql rugby -f loaders/load_games_new.sql

rm /tmp/data/*.csv
rmdir /tmp/data
rm /tmp/games.csv
