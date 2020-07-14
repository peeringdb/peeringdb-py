#!/bin/bash

[[ $# -eq 1 ]] || { echo "usage: $(basename $0) dbfile"; exit 1; }

DBFILE="$1"
SCHEMA=$(mktemp --suffix=".schema.sql")
DUMP=$(mktemp --suffix=".dump.sql")
DATA="$DBFILE.data.sql"

DUMP_SCRIPT="$(dirname $0)/dump_sqlite.py"

sqlite3 "$DBFILE" .schema > $SCHEMA
# sqlite3 "$DBFILE" .dump > $DUMP
python3 $DUMP_SCRIPT "$DBFILE" > $DUMP
grep -vx -f $SCHEMA $DUMP > $DATA
