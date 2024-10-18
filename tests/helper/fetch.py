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

    def fetch(self, R, pk, depth):
        return __data[R][pk]

    def fetch_latest(self, R, pk, depth=0):
        return self.fetch(R, pk, depth), None

    def fetch_all_latest(self, R, params={}, depth=0):
        return list(__data[R].values())

    def fetch_deleted(self, R, pk, depth=0):
        return __deleted[R][pk]
