"""
utility function that builds cache files from test.peeringdb.com/api for testing purposes
"""

import copy
import json
import os

import requests

import peeringdb
from peeringdb.client import Client
from peeringdb.resource import _NAMES as objs
from peeringdb.resource import RESOURCES_BY_TAG

CONFIG = {
    "orm": {
        "backend": "django_peeringdb",
        "database": {
            "engine": "sqlite3",
            "host": "",
            "name": ":memory:",
            "password": "",
            "port": 0,
            "user": "",
        },
        "secret_key": "",
        "migrate": True,
    },
    "sync": {
        "url": "https://test.peeringdb.com/api",
        "user": "",
        "password": "",
        "only": [],
        "strip_tz": 1,
        "timeout": 0,
        # we dont want to use caching during normal tests
        # caching will be tested specifically, so keep blank
        "cache_url": "",
    },
}


def get_client():
    return Client(CONFIG)


def build_cache_files():
    tags = objs.keys()
    client = get_client()
    B = peeringdb.get_backend()
    from django_peeringdb.models.concrete import tag_dict

    for tag in tags:
        url = f"https://test.peeringdb.com/api/{tag}?depth=0"
        response = requests.get(url)

        # Make sure the request was successful
        if response.status_code == 200:
            data = response.json()

            # store the json data to a file in data/cache directory
            cache_file_path = os.path.join("data", "cache", f"{tag}-0.json")
            with open(cache_file_path, "w") as file:
                json.dump(data, file, indent=4)
            print(f"Successfully fetched and stored data for {tag} in cache directory")

            # store the json data to a file in data/full directory in Django fixture format
            full_file_path = os.path.join("data", "full", f"{tag}.json")
            full_nonunique_file_path = os.path.join(
                "data", "full_nonunique", f"{tag}.json"
            )

            fixture_data = []
            model = tag_dict[tag]
            for item in data["data"]:
                fields = {}

                for k, v in item.items():
                    if isinstance(v, list):
                        continue
                    if hasattr(model, k):
                        fields[k] = v

                fields["created"] = fields["created"][:-1]
                fields["updated"] = fields["updated"][:-1]

                fields.pop("id")

                fixture_item = {
                    "model": f"django_peeringdb.{model.__name__.lower()}",
                    "pk": item["id"],
                    "fields": fields,
                }
                fixture_data.append(fixture_item)
            with open(full_file_path, "w") as file:
                json.dump(fixture_data, file, indent=4)

            with open(full_nonunique_file_path, "w") as file:
                if tag == "net":
                    # copy the last entry with diff name, asn and pk
                    fixture_item = copy.deepcopy(fixture_data[-1])
                    fixture_item["fields"]["name"] = "net FAKE"
                    fixture_item["fields"]["asn"] += 100
                    fixture_item["pk"] += 1
                    fixture_data.append(fixture_item)

                    for data in fixture_data:
                        data["fields"]["name"] = f"net {data['pk']}"

                json.dump(fixture_data, file, indent=4)

            print(
                f"Successfully stored data for {tag} in full directory in Django fixture format"
            )
        else:
            print(f"Failed to fetch data for {tag}")


if __name__ == "__main__":
    build_cache_files()
