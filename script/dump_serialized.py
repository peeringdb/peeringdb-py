import json
import sys
from pathlib import Path

from django.core import serializers

import peeringdb


def client_dump(client):
    for q in client.tags.all():
        ser = serializers.serialize("json", q.all())
        yield q.res, ser


def client_load(client):
    dump = {}
    for qs in client.tags.all():
        ser = serializers.serialize("json", qs.all())
        dump[qs.res.tag] = json.loads(ser)
    return dump


def main(filepath):
    client = peeringdb.PeeringDB()
    dump = client_dump(client)
    path = Path(filepath)
    assert path.is_dir(), path

    for _ in client.tags.all():
        # FIXME: what's happenig here?
        with open(path / f"{res}.json", "w") as out:
            out.write()
    with open(filepath, "w") as f:
        json.dump(dump, f)

    return 0


if __name__ == "__main__":
    exit(main(sys.argv[1:]))
