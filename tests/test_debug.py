import http.client
import importlib

import peeringdb._debug.http as debug_http
from peeringdb import _debug


def test_log_validation_errors_covers_both_branches():
    class MissingError(Exception):
        pass

    class FakeField:
        pass

    class FakeBackend:
        def get_field(self, obj, k):
            return FakeField()

        def object_missing_error(self):
            return MissingError

    class FakeObj:
        asn = 123

        @property
        def broken(self):
            raise MissingError()

    class FakeError(Exception):
        message_dict = {"asn": ["e1"], "broken": ["e2"]}

    # "asn" exercises the happy path; "broken" raises -> the except branch
    _debug.log_validation_errors(FakeBackend(), FakeError(), FakeObj(), "k")


def test_debug_http_module_enables_debuglevel():
    original = http.client.HTTPConnection.debuglevel
    try:
        importlib.reload(debug_http)
        assert http.client.HTTPConnection.debuglevel == 1
    finally:
        http.client.HTTPConnection.debuglevel = original
