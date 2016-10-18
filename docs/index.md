
# PeeringDB Python Client

This is the first release of our client package, it's fairly new, but we're releasing early to get feedback as soon as possible.

## How to install
For those unfamiliar with python, you'll usually want to install to a separate [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

    virtualenv pdbvenv
    . pdbvenv/bin/activate

Install the peeringdb package with

    pip install peeringdb

## What's included?

There's currently a hard dependency on django_peeringdb, so the django models are included.

By installing the package, you get both a [client library](api.md) and a [command line utility](cli.md).

## Configuration
Both command line and library will try to use a common config file, by default located at `~/.peeringdb/config.yaml`

You can go through a setup wizard to configure and create the config (also downloads any needed requirements) with:

    peeringdb configure

Alternatively, to write a config file with the defaults:

    peeringdb conf_write

Then edit the file it created (default `~/peeringdb/config.yaml`). Currently, it directly uses django, so any database backend django supports will work, for example, to sync to MySQL, you could use the following database config:

    database:
      engine: mysql
      host: localhost
      name: peeringdb
      user: peeringdb
      password: supers3cr3t

After everything is configured, check your setup and install any new dependencies with:

    peeringdb depcheck

## Platform Tips
### Ubuntu / Debian
If you have issues building the mysqlclient install the dev libraries:

    sudo apt install libmysqlclient-dev
