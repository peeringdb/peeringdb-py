# some objects contain private data that is not
# available on cached responses
#
# if --fetch-private is specified, these objects
# will always be fetched from the API
PRIVATE_OBJECTS: list[str] = ["poc", "ixlan"]
