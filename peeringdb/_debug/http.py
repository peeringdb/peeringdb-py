import logging
import http.client

http.client.HTTPConnection.debuglevel = 1

requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
