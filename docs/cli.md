
# Command Line Interface

    Usage: peeringdb [OPTIONS] COMMAND [ARGS]...

      PeeringDB

    Options:
      --version      Show the version and exit.
      --list-codecs  list available codecs
      --help         Show this message and exit.

    Commands:
      conf_write  write config file with defaults
      configure   configure peeringdb
      depcheck    check for dependencies, install if necessary
      get         get an object from peeringdb
      sync        synchronize to a local database

## Commands

### conf_write
Writes a config file with all options and defaults to the config directory (changable with -c)

### configure
Prompts user for input to configure local database

### depcheck
Checks for dependencies and installs any needed packages

### get `<obj><id>`
Fetches a specific object and outputs to stdout

You may use the CLI to dump any object in the database with <object tag><id>, for example:

    peeringdb get net1

You may also change the output format to anything munge supports, so to get json, it would be:

    peeringdb -O json get net1


### sync
Synchronizes PeeringDB to a local database

After doing a full sync, it only updates objects that have changed, so it's safe / efficient to run it as often as you want.

By default, peeringdb will sync to a file in the config dir called peeringdb.sqlite3 - to change that, see [configuration](index.md#configuration)

Then edit the file it created (default `~/peeringdb/config.yaml`). Currently, it directly uses django, so any database backend django supports will work, for example, to sync to MySQL, you could use the following database config:

    database:
      engine: mysql
      host: localhost
      name: peeringdb
      user: peeringdb
      password: supers3cr3t

For MySQL, you need to use utf8 and a utf8 collation before doing the initial sync, for example:

New database:

    CREATE DATABASE peeringdb DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;

or existing database

    ALTER DATABASE peeringdb DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;

Once the database is configured how you'd like it, you can do an initial sync of the database with

    peeringdb sync

Then add a cron job to keep it in sync, for example, once a day at between midnight and midnight plus 10 minutes, with random sleep delay to prevent thundering hurd

    crontab -l | { cat; echo "`expr $RANDOM % 60` 0 * * * `which peeringdb` sync > /dev/null 2>&1"; } | crontab -

Or, if your cron supports random:

    crontab -l | { cat; echo "0 0 * * * sleep \$[RANDOM\%600] ; `which peeringdb` sync > /dev/null 2>&1"; } | crontab -

