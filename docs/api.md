# Application Programming Interface
## Instantiate

    from peeringdb import config, resource
    from peeringdb.client import Client

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

    from peeringdb import config, resource
    from peeringdb.client import Client

    pdb = Client()

    # sync database with remote data
    # unauthenticated to default URL unless configured
    # since this is relatively slow, normally this would be done from cron - see CLI doc for example
    pdb.update_all()

    # get a single record
    n1 = pdb.get(resource.Network, 1)

    net = pdb.tags.net              # type wrap

    # both are equal
    assert net.get(1) == n1

    print(n1)
    
    # query by parameter
    print(pdb.all(resource.Network).filter(asn=2906))
    # or
    print(net.all().filter(asn=2906))

## Tip - Custom config file location

    import yaml
    from peeringdb import config, resource
    from peeringdb.client import Client

    with open("../example.yaml") as file:
            cfg = yaml.load(file, Loader=yaml.FullLoader)

    pdb = Client(cfg=cfg)
    
    print(pdb.get(resource.Network, 1))
