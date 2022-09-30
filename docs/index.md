# PeeringDB Python Client
This is an early release of our client package, it's fairly new, but we're releasing early to get feedback as soon as possible.

This release represents a redesign and refactor of the Python client.

## What's included?
By installing the package, you get both a [client library](api.md) and a [command line utility](cli.md).

## What's new?
The object-relational mapping backend is now configurable. Therefore, the dependency on `django_peeringdb` is now a soft dependency. However, it is currently the only available backend, so it will still need to be installed.

Submissions and requests for new backend modules are welcome.

### Migrating from old version
Old databases should be compatible with this version of `peeringdb` as long as the version of the backend used is compatible. This version can be checked with `peeringdb.get_backend_info()[1]` after initializing the client.

## How to install
For those unfamiliar with python, you'll usually want to install to a separate [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

    virtualenv pdbvenv
    source pdbvenv/bin/activate

Install the peeringdb package with

    pip install peeringdb

Install Django and the Django backend with:

    pip install django
    pip install django_peeringdb

## Configuration
Both command line and library will try to use a common config file, by default located at `~/.peeringdb/config.yaml`

You can go through a setup wizard to configure and create the config (also downloads any needed requirements) with:

    peeringdb config set

To skip the wizard and write a config file with the defaults:

    peeringdb config set -n

Then edit the file it created (default `~/.peeringdb/config.yaml`). Currently, since only Django is supported, any database backend Django supports will work, for example, to sync to MySQL, you could use the following database config:

    database:
      engine: mysql
      host: localhost
      name: peeringdb
      user: peeringdb
      password: supers3cr3t

If you provide authentication in your config file, it will include contacts much like version 1 did.

<!-- After everything is configured, check your setup and install any new dependencies with: -->
<!--     peeringdb depcheck -->

## Authentication
To sync with peeringdb API servers, you need to provide authentication. Basic authentication is supported, but you can also use your API keys. To sync with PeeringDB, you can add the following config:


    sync:
        api_key: 'YOUR_API_KEY_HERE'
        user: 'username'
        password: 'password'
        only: []
        strip_tz: 1
        timeout: 0
        url: https://peeringdb.com/api

This will also be prompted during the configuration wizard.

Please take note that only one authentication method is supported, either basic or API key.

## Tips
### MySQL
You need to use utf8 and a utf8 collation before doing the initial sync.

New database:

    CREATE DATABASE peeringdb DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;

or existing database:

    ALTER DATABASE peeringdb DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;

### pip and setuputils
If you are getting the error `'install_requires' must be a string or list of strings containing valid project/version requirement specifiers; Expected ',' or end-of-list in ipaddress>=1; python_version<'3.3' at ; python_version<'3.3'`, update pip and setuptools.

```sh
pip install -U pip
pip install -U setuptools
```

### Ubuntu / Debian
If you have issues building the mysqlclient install the dev libraries:

    sudo apt install libmysqlclient-dev

### Sample Install & Upgrade Steps
Example install & upgrade steps are at [https://lists.peeringdb.com/pipermail/pdb-tech/2022-September/000444.html](https://lists.peeringdb.com/pipermail/pdb-tech/2022-September/000444.html).
