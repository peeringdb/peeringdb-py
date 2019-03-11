"""
RPC / REST client implementation module
"""
import re
import requests
from twentyc.rpc import RestClient
from twentyc.rpc.client import NotFoundException, PermissionDeniedException, InvalidRequestException

import peeringdb


class CompatibilityError(Exception):
    pass


class Fetcher(RestClient):
    """
    REST client with some patches
    """

    def __init__(self, **kwargs):
        # self.return_error = True
        super(Fetcher, self).__init__(**kwargs)

    def _req(self, func):
        try:
            return func(), None
        except NotFoundException as e:  # 404
            return {}, e
        except PermissionDeniedException as e:  # 401
            return {}, e
        except InvalidRequestException as e:
            pattern = 'client version is incompatible'
            error = e.extra['meta']['error']
            if re.search(pattern, error):
                raise CompatibilityError(error)
            raise

    def fetch(self, R, pk, depth):
        return self._req(lambda: self.get(R.tag, pk, depth=depth))

    def fetch_latest(self, R, pk, depth, since=None):
        backend = peeringdb.get_backend()
        if since is None:
            since = backend.last_change(backend.get_concrete(R))
        if since:
            since = since+1
        return self._req(lambda: self.get(R.tag, pk, since=since, depth=depth))

    def fetch_all(self, R, depth, params={}):
        params = {
            k: ','.join(map(str, v)) if isinstance(v,
                                                   (list, tuple)) else v
            for k, v in params.items()
        }
        return self._req(lambda: self.all(R.tag, depth=depth, **params))

    def fetch_all_latest(self, R, depth, params={}, since=None):
        backend = peeringdb.get_backend()

        if since is None:
            since = backend.last_change(backend.get_concrete(R))

        if since:
            since = since+1
        params = {
            k: ','.join(map(str, v)) if isinstance(v,
                                                   (list, tuple)) else v
            for k, v in params.items()
        }
        return self._req(
            lambda: self.all(R.tag, since=since, depth=depth, **params))

    def fetch_deleted(self, R, pk, depth):
        def req():
            return self.all(R.tag, id=pk, since=1, depth=depth)

        return self._req(req)

    # fixme:
    # RestClient monkeypatches to add headers to request

    def get(self, typ, id, **kwargs):
        """
        Load type by id
        """
        return self._load(self._request(typ, id=id, params=kwargs))

    def _request(self, typ, id=0, method='GET', params=None, data=None,
                 url=None):
        """
        send the request, return response obj
        """
        backend, backend_version = peeringdb.get_backend_info()
        user_agent = 'PeeringDB/{} {}/{}'.format(peeringdb.__version__,
                                                 backend, backend_version)
        headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        auth = None

        if self.user:
            auth = (self.user, self.password)
        if not url:
            if id:
                url = "%s/%s/%s" % (self.url, typ, id)
            else:
                url = "%s/%s" % (self.url, typ)

        return requests.request(method, url, params=params, data=data,
                                auth=auth, headers=headers)
