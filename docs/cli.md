# Command Line Interface

    $ peeringdb -h
    usage: peeringdb [-h] [--version] [-C CONFIG_DIR] {sync,get,whois,config} ...

    positional arguments:
      {sync,get,whois,config}
        sync                Synchronize local tables to PeeringDB
        get                 Get a resource
        whois               Simulate a whois lookup supports as<ASN> : query by AS
                            ixlans<net id> : query networks on an IX
        config              Configuration management

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      -C CONFIG_DIR, --config-dir CONFIG_DIR
                            Directory containing configuration files

# Commands
## Configuration
### config show
Outputs current config.

### config set
Prompts user for input to configure local database.

With -n, writes a config file with all options and defaults to the config directory (changable with -C).

Example:
    $ peeringdb -C ~/.new-config/ config set -n

### config list-codecs
Lists available config codec formats.

## get `<obj><id>`
Fetches a specific object and outputs to stdout.

You may use the CLI to dump any object in the database with <object tag><id>, for example:

    peeringdb get net1

By default, this produces a shallow output (depth = 0). Set the depth with `--depth`/`-D`:

    peeringdb get net1 -D2

You may also change the output format to anything munge supports, so to get json, it would be:

    peeringdb -O json get net1

## whois `<obj><id>`
Fetches a specific object and outputs to stdout, supports everything that `get` does, as well as:

* `as<ASN>` : query by AS
* `ixlans<net id>` : query networks on an IX

## drop-tables

!!! Error "Warning"
    This will delete data.

Drops all peeringdb tables.

## sync
Synchronizes PeeringDB to a local database.

After doing a full sync, it only updates objects that have changed.

By default, peeringdb will sync to a file in the config dir called `peeringdb.sqlite3` - to change that, see [configuration](index.md#configuration)

Once the database is configured how you'd like it, you can do an initial sync of the database with

    peeringdb sync

Then add a cron job to keep it in sync, for example, once a day at between midnight and midnight plus 10 minutes, with random sleep delay to prevent thundering herd:

    crontab -l | { cat; echo "$(expr $RANDOM % 60) 0 * * * $(which peeringdb) sync > /dev/null 2>&1"; } | crontab -

Or, if your cron supports random:

    crontab -l | { cat; echo "0 0 * * * sleep \$[RANDOM\%600] ; $(which peeringdb) sync > /dev/null 2>&1"; } | crontab -


## local server

This document outlines the server related commands of the `peeringdb` CLI. These commands help the user to manage a local peeringdb server snapshot for `peeringdb`.

### Setup server

The following command will build and setup the PeeringDB server container.

```sh
$ peeringdb server --setup
```

### Start server

The following command will start the PeeringDB server container.

```sh
$ peeringdb server --start
```

### Stop server

The following command will stop the PeeringDB server container.

```sh
$ peeringdb server --stop
```

## Error Handling

If you try to start or stop the server without running the setup first, you will see an error stating that the `peeringdb_server` directory was not found. If this happens, run the `--setup` command and then try again.