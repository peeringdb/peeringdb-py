"""
Module defining main interface classes for sync
"""

import logging
from datetime import datetime
from typing import List, Union

from peeringdb import _config_logs, get_backend
from peeringdb._sync import extract_relations, set_many_relations, set_single_relations
from peeringdb.fetch import Fetcher
from peeringdb.private import private_data_has_been_fetched
from peeringdb.util import group_fields


class Updater:
    """
    Handles initial and incremental update from a PeeringDB remote API
    to the local backend.

    The updater is responsible for creating and updating objects in the local
    backend. It does this by fetching objects from the remote API and creating
    or updating the corresponding objects in the local backend.
    """

    def __init__(self, fetcher: Fetcher):
        _config_logs()
        self._log = logging.getLogger(__name__)
        self.resources = {}
        self.backend = get_backend()
        self.fetcher = fetcher

    def copy_object(self, new):
        """
        Copies a new object to an existing one
        :return:
        """
        old = self.backend.get_object(new.__class__, new.id)
        for field in self.backend.get_fields(new.__class__):
            try:
                setattr(old, field.name, getattr(new, field.name))
            except TypeError as e:
                if "Direct assignment" in str(e):
                    pass  # Ignore refs
                else:
                    raise

        self.clean_obj(old)
        self.backend.save(old)

    def clean_obj(self, obj):
        """
        Run object through backend validation

        Will raise an exception if the object is not valid
        """

        try:
            self.backend.clean(obj)
        except self.backend.validation_error() as e:
            # e.message_dict contains field names as keys and lists of errors as values
            for errors in e.message_dict.values():
                for error in errors:
                    # Checking if the error message is the one we want to ignore
                    # field is allowed to be None in the db, but not blank according to backend
                    # validation. We ignore this error since the data is already validated
                    # and writing None to the db is fine.
                    if error != "This field cannot be blank.":
                        raise e

    def create_obj(self, row: dict, res) -> (any, bool):
        """
        Create a model instance from a row
        :param row: Object from API
        :param res: Resource to create
        """
        _, dangling = extract_relations(self.backend, res, row)
        for resource, pks in dangling.items():
            for pk in pks:
                # Check if we have it
                rel_obj = None
                try:
                    self.backend.get_object(self.backend.get_concrete(resource), pk)
                except self.backend.object_missing_error(
                    self.backend.get_concrete(resource)
                ):
                    # We dont have the dangling relationship, so we try to fetch it
                    # from the api and create it.

                    self._log.info("Fetching dangling relationship %s %s", resource, pk)
                    related_row = self.fetcher.get(resource.tag, pk)

                    # instantiate the relationship object

                    rel_obj, _ = self.create_obj(related_row, resource)
                    try:
                        self.clean_obj(rel_obj)
                    except self.backend.validation_error() as e:
                        self._log.error(
                            "Failed to clean dangling object %s %s: %s", resource, pk, e
                        )
                        return None, False

                    # save the relationship object

                    if rel_obj:
                        self.backend.save(rel_obj)

        # Initialize object
        field_groups = group_fields(self.backend, self.backend.get_concrete(res))
        try:
            obj = self.backend.get_object(self.backend.get_concrete(res), row["id"])
        except self.backend.object_missing_error(self.backend.get_concrete(res)):
            tbl = self.backend.get_concrete(res)
            obj = tbl()

        # set_scalars
        for fname, field in field_groups["scalars"].items():
            value = row.get(fname, getattr(obj, fname, None))
            value = self.backend.convert_field(obj.__class__, fname, value)

            # TODO: datetimes are strings for some reason
            if (
                fname in ["created", "updated", "rir_status_updated", "ixf_last_import"]
                and isinstance(value, str)
            ) or (getattr(obj, "tzinfo", None) is not None):
                value = datetime.fromisoformat(value.rstrip("Z"))
            # elif isinstance(value, str) and "T" in value and "Z" in value and "-" in value:
            #     print("NOT DATETIME", fname, value, type(value))

            # Remove timezone info
            if isinstance(value, datetime):
                value = value.replace(tzinfo=None)

            setattr(obj, fname, value)
            self._log.debug("  %s: %s (%s)", fname, value, type(value))

        set_single_relations(self.backend, res, obj, row)
        set_many_relations(self.backend, res, obj, row)

        try:
            self.clean_obj(obj)
        except self.backend.validation_error() as e:
            self._log.debug("[%s] Failed to clean %s %s: %s", res.tag, res, obj, e)
            if "already exists" in str(e):
                self.update_collision(res, row, e)
                self.clean_obj(obj)
            return obj, True

        return obj, False

    def _handle_initial_sync(self, entries: list, res):
        """
        Called during the first sync of a resource

        This will do a batch create of all objects in the resource
        :param entries: List of objects from API
        :param res: Resource to sync
        """

        objs = []
        retry = []
        for row in entries:
            obj, ret = self.create_obj(row, res)
            if ret:
                retry.append(row)
            elif obj:  # not retry and obj
                objs.append(obj)
        for row in retry:
            obj, _ = self.create_obj(row, res)
            objs.append(obj)

        self.backend.get_concrete(res).objects.bulk_create(objs)

    def _handle_incremental_sync(self, entries: list, res):
        """
        Called during an incremental sync of a resource (i.e. not the first sync)

        Entries will only contain objects that have changed since the last sync
        :param entries: List of objects from API
        :param res: Resource to sync
        """

        for row in entries:
            try:
                self.backend.get_object(self.backend.get_concrete(res), row["id"])
                obj, _ = self.create_obj(row, res)
                self.copy_object(obj)
            except self.backend.object_missing_error(self.backend.get_concrete(res)):
                obj, _ = self.create_obj(row, res)
                self.backend.save(obj)

    def update_all(
        self,
        rs: List[any],
        since: int = None,
        skip: Union[List[str], None] = None,
        fetch_private: bool = False,
    ):
        """
        Update all objects of a given type
        :param rs: List of resources to update
        :param since: Unix timestamp of last update
        :param skip: List of resource tags to skip
        """

        for res in rs:
            if skip is not None:
                for i in skip:
                    self.fetcher.load(i, since)

            if skip and res.tag in skip:
                self._log.info("[%s] Skipping", res.tag)
                continue

            if since is None:
                _since = self.backend.last_change(self.backend.get_concrete(res))
            else:
                _since = since

            initial_private = False
            if fetch_private:
                initial_private = not private_data_has_been_fetched(self.backend, res)

            self.fetcher.load(
                res.tag,
                _since + 1 if _since else None,
                fetch_private=fetch_private,
                initial_private=initial_private,
            )
            entries = self.fetcher.entries(res.tag)
            self._log.info("[%s] Processing %d objects", res.tag, len(entries))

            if not _since:
                self._handle_initial_sync(entries, res)
            else:
                self._handle_incremental_sync(entries, res)

    def update_one(self, res, pk: int, depth=0):
        """
        Update a single object
        :param res: Resource to update
        :param pk: Primary key of object to update
        :param depth: Depth of recursion
        :return:
        """
        if depth != 0:
            # no longer relevant, deprecation warning
            self._log.warning(
                "update_one: depth parameter is not used and will be removed in a future version"
            )

        row = self.fetcher.get(res.tag, pk, depth=0, force_fetch=True)
        # create object instance (unsaved)
        obj, _ = self.create_obj(row, res)
        try:
            # attempt update existing instance of object (if exists, will save)
            self.copy_object(obj)
        except self.backend.object_missing_error(self.backend.get_concrete(res)):
            # object does not exist, create object instance and save as
            # new object
            obj, _ = self.create_obj(row, res)
            self.backend.save(obj)

    def update_collision(self, res, row: dict, exc: Exception):
        """
        Sometimes we encounter edge-case collisions triggered by a
        unique constraint validation error. This function attempts to
        resolve the collision by updating the colliding object from the api
        :param res: Resource to update
        :param row: Row from API
        :param exc: Exception raised by validation error
        """

        filters = {}
        for field, error_message in exc.error_dict.items():
            if "already exists" in str(error_message):
                filters[field] = row[field]

        for field, value in filters.items():
            self._log.debug(
                "[%s] Updating collision %s %s=%s", res.tag, res, field, value
            )
            collision = self.backend.get_object_by(
                self.backend.get_concrete(res), field, value
            )
            self.update_one(res, collision.id)
