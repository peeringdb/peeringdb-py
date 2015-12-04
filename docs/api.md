
# Application Program Interface

## Instantiate
    from peeringdb import PeeringDB

    pdb = PeeringDB()

## Calls

### all
    def all(self, typ, **kwargs):

Gets all objects of specified type, matching query from kwargs, valid kwargs are available [here](http://docs.peeringdb.com/api_specs/#operations).

### get
    def get(self, typ, id, **kwargs):

Gets a single object of specified type and id, matching query from kwargs, valid kwargs are available [here](http://docs.peeringdb.com/api_specs/#operations).

### create
    def create(self, typ, data, return_response=False):

Create an object of specified type from data.

### update
    def update(self, typ, id, **kwargs):

Update an object of specified type from kwargs.

### save
    def save(self, typ, data):

Saves object of specified type from data.

### rm
    def rm(self, typ, id):

Removes specified object.

### type_wrap
    def type_wrap(self, typ):

Returns an object that directly does operations on the specified type.


## Full Example

    # unauthenticated to default URL (unless ~/.peeringdb/config.yaml exists)
    from peeringdb import PeeringDB

    pdb = PeeringDB()

    # get a single record
    net = pdb.type_wrap('net')
    # both are equal
    assert net.get(1) == pdb.get('net', 1)

    # query by parameter
    pdb.all('net', asn=2906)
    # or
    net.all(asn=2906)

