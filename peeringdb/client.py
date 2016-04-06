
import munge.util
from peeringdb import config
import twentyc.rpc


class PeeringDB(twentyc.rpc.RestClient):
    def __init__(self, **kwargs):
        """
        options:
            conf_dir : directory to load config from
            url      : URL to connect to
            user     : user to connect as
            password : password to use
            timeout  : timeout to fail after
        """
        # try to load config
        cfg = config.get_config(conf_dir=kwargs.get('conf_dir', config.default_conf_dir))
        self.config = cfg['peeringdb']
        # override config with kwargs
        munge.util.recursive_update(self.config, kwargs)
        super(PeeringDB, self).__init__(**self.config)

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

