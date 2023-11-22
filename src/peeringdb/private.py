from peeringdb.backend import Interface

# some objects contain private data that is not
# available on cached responses
#
# if --fetch-private is specified, these objects
# will always be fetched from the API
PRIVATE_OBJECTS = ["poc", "ixlan"]


def private_data_has_been_fetched(backend: Interface, res: object):
    if res.tag not in PRIVATE_OBJECTS:
        return False

    concrete = backend.get_concrete(res)

    if res.tag == "poc":
        return backend.get_objects_by(concrete, "visible", "Users").count() > 0

    if res.tag == "ixlan":
        objs = backend.get_objects_by(
            concrete, "ixf_ixp_member_list_url_visible", "Private"
        )
        return objs.filter(ixf_ixp_member_list_url__isnull=False).count() > 0
