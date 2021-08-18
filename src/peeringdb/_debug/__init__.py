import logging

# import pdb


def log_validation_errors(B, e, obj, k):
    log = logging.getLogger("peeringdb.sync")
    log.debug("{} : errors: {}".format(e, e.message_dict))
    for k, v in e.message_dict.items():
        field = B.get_field(obj, k)
        try:
            log.debug("{}: {}, dict: {}".format(k, getattr(obj, k), field.__dict__))
        except B.object_missing_error():
            log.debug("{}: Missing Object, dict: {}".format(k, field.__dict__))


def try_or_debug(f):
    try:
        return f()
    except Exception:
        # pdb.set_trace() ???
        raise
