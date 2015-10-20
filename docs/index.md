
# PeeringDB Python Client

This is the first release of our client package, it's fairly new, but we're releasing early to get feedback as soon as possible.

## How to install
For those unfamiliar with python, you'll usually want to install to a separate [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

    virtualenv pdbvenv
    . pdbvenv/bin/activate

Then install the peeringdb package with

    pip install peeringdb

## What's included?

There's currently a hard dependency on django_peeringdb, so the django models are included.

By installing the package, you get both a [client library](api.md) and a [command line utility](cli.md).

## Configuration
Both command line and librarys will try to use a common config file, by default located at `~/.peeringdb/config.yaml`


