#!/usr/bin/env python3
#
# Like sqlite .dump, but add explicit column names to INSERT statements

import re
import sqlite3
import sys

RE_INSERT_INTO = re.compile(r'INSERT INTO "(\w+)"')

SQL_TABLES = "SELECT name FROM sqlite_master WHERE type='table';"
SQL_TABLE_INFO = "PRAGMA TABLE_INFO(%s)"


def add_colnames(line, fields):
    m = RE_INSERT_INTO.match(line)
    if not m:
        return line
    name = m[1]
    if name.startswith("sqlite_"):
        return line
    colnames = ", ".join(f'"{field}"' for field in fields[name])
    return line.replace("VALUES", f"({colnames}) VALUES")


def main(file, dumpfile=None):
    with open(file):
        pass  # sqlite will create if not found
    con = sqlite3.connect(file)
    tables = [name for (name,) in con.execute(SQL_TABLES).fetchall()]
    fields = {}
    for name in tables:
        cols = con.execute(SQL_TABLE_INFO % name).fetchall()
        fields[name] = [c[1] for c in cols]

    output = [add_colnames(line, fields) for line in con.iterdump()]

    def write(f):
        for line in output:
            f.write("%s\n" % line)

    if dumpfile is None:
        write(sys.stdout)
    else:
        with open(dumpfile, "w") as f:
            write(f)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
