# Application Programming Interface
## Instantiate

    from peeringdb import Client
    pdb = Client()

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

    from peeringdb import Client, config, resource

    pdb = Client()

    # sync database with remote data
    # unauthenticated to default URL unless configured
    pdb.update_all()

    # get a single record
    n1 = pdb.get(resource.Network, 1)

    net = pdb.tags.net              # type wrap

    # both are equal
    assert net.get(1) == n1

    # query by parameter
    pdb.all(resource.Network).filter(asn=2906)
    # or
    net.all().filter(asn=2906)
