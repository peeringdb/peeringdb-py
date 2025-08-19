from twentyc.rpc import RestClient

from peeringdb.resource import Network

from . import _data

# try: from peeringdb import _debug_http
# except: pass

__data = {Network: {20: _data.twentyc}}

__deleted = {Network: {}}


class Fetcher(RestClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fetch(self, resource, pk, depth):
        return __data[resource][pk]

    def fetch_latest(self, resource, pk, depth=0):
        return self.fetch(resource, pk, depth), None

    def fetch_all_latest(self, resource, params={}, depth=0):
        return list(__data[resource].values())

    def fetch_deleted(self, resource, pk, depth=0):
        return __deleted[resource][pk]
