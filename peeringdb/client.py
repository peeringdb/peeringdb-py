
import munge.util
from peeringdb import config
import twentyc.rpc


class PeeringDB(twentyc.rpc.RestClient):
    def __init__(self, **kwargs):
        # try to load config
        cfg = config.get_config(conf_dir=kwargs.get('conf_dir', config.default_conf_dir))
        pdb = cfg['peeringdb']
        # override config with kwargs
        munge.util.recursive_update(pdb, kwargs)
        super(PeeringDB, self).__init__(**pdb)

    def asn(self, pk):
        return self.all('net', asn=pk, depth=2)

    def ixnets(self, pk):
        return self.all('net', ix_id__in=pk, depth=2)

    def whois(self, typ, pk, **kwargs):
        if typ == 'as':
            return ('net', self.asn(pk))
        elif typ == 'ixnets':
            return ('net', self.ixnets(pk))
        else:
            return (typ, self.get(typ, pk, **kwargs))

