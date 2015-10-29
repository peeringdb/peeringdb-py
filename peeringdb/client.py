
import munge.util
from peeringdb import config
import twentyc.rpc


class PeeringDB(twentyc.rpc.RestClient):
    def __init__(self, **kwargs):
        # try to load config
        cfg = config.get_config()
        pdb = cfg['peeringdb']
        # override config with kwargs
        munge.util.recursive_update(pdb, kwargs)
        super(PeeringDB, self).__init__(**pdb)

#    def all(self, typ, **kwargs):
#        """
#        List all of type
#        Valid arguments available at
#            http://docs.peeringdb.com/api_specs/#operations
##        Currently:
#            depth : int nested sets will be loaded (slow)
#            fields : str comma separated list of field names - only matching
#                fields will be returned in the data
##            since : int timestamp (UTC) only get objects modified after this
#            skip : number of records to skip
#            limit : number of records to limit request to
##            [field_name] : int|string queries for fields with matching value
#        """
#        return self.rpc.all(typ, **kwargs)
#
#    def get(self, typ, id):
#        """
#        Load type by id
##        """
#        return self._load(self._request(self._url(typ, id)))
