
# Command Line Interface

    usage: peeringdb [-h] [-c CONFIG] [-O OUTPUT_FORMAT] [--list-codecs] [cmd]

    positional arguments:
      cmd                   subcommand {sync,conf_write,<obj><id>} (default: None)

    optional arguments:
      -h, --help            show this help message and exit
      -c CONFIG, --config CONFIG
                            config directory (default: ~/.peeringdb)
      -O OUTPUT_FORMAT, --output-format OUTPUT_FORMAT
                            output data format (default: yaml)
      --list-codecs         list all available codecs (default: False)

### conf_write
Writes a config file with all options and defaults to the config directory (changable with -c)

### sync
Synchronizes PeeringDB to a local database

### `<obj><id>`
Fetches a specific object and outputs to stdout

## Configuration

## Fetching objects

You may use the CLI to dump any object in the database with <object tag><id>, for example:

    peeringdb net1

You may also change the output format to anything munge supports, so to get json, it would be:

    peeringdb -O json net1

## Local database sync

After doing a full sync, it only updates objects that have changed, so it's safe / efficient to run it as often as you want.

By default, peeringdb will sync to a file in the config dir called peeringdb.sqlite3 - to change that:

    peeringdb conf_write

Then edit the file it created (default `~/peeringdb/config.yaml`). Currently, it directly uses django, so any database backend django supports will work, for example, to sync to MySQL, you could use the following database config:

    database:
      engine: mysql
      host: localhost
      name: peeringdb
      user: peeringdb
      password: supers3cr3t

Once the database is configured how you'd like it, you can do an initial sync of the database with

    peeringdb sync

Then add a cron job to keep it in sync, for example, once a day at midnight

    crontab -l | { cat; echo "0 0 * * * `which peeringdb` sync > /dev/null 2>&1"; } | crontab -
