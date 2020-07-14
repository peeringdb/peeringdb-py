import sys
from pathlib import Path

import peeringdb
from peeringdb.util import client_dump

def main(filepath):
    client = peeringdb.PeeringDB()
    path = Path(filepath)
    client_dump(client, path)

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
