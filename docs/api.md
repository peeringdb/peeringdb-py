# Application Programming Interface
## Instantiate

    from peeringdb import PeeringDB
    pdb = PeeringDB()

## Calls
Methods on `Client` correspond directly to PeeringDB REST API calls.

### `get(self, res, id)`
Gets a single object of specified type and id.

### `all(self, res, **kwargs)`
Gets all objects of specified type, matching query from kwargs, valid kwargs are available [here](http://docs.peeringdb.com/api_specs/#operations).

### `query(self, res)`
Returns a wrapper object that directly performs operations on data of the specified resource type.

### `update(self, res, id, **kwargs)`
Update an object of specified type from kwargs.

## Full Example

    from peeringdb import PeeringDB, config, resource

    # same as PeeringDB(config.load_config())
    pdb = PeeringDB()

    # sync database with remote data
    # unauthenticated to default URL unless configured
    pdb.update_all()

    # get a single record
    n1 = pdb.get(resource.Network, 1)

    # equivalently:
    net = pdb.tags.net              # type wrap - new method
    # net = pdb.type_wrap('net')      # old method

    # both are equal
    assert net.get(1) == n1

    # query by parameter
    pdb.all(resource.Network, asn=2906)
    # or
    net.all(asn=2906)
