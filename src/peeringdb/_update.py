"""
Module defining main interface classes for sync
"""
import logging
import threading
from contextlib import contextmanager
from datetime import datetime

from peeringdb import _config_logs, _fetch, _sync
from peeringdb import _tasks_sequential as _tasks
from peeringdb import get_backend, resource

wrap_generator = _tasks.wrap_generator


class _CancelSave(Exception):
    "Token exception to cancel transaction"


class Updater:
    """
    Class for updating resource data.

    Arguments:
        - fetcher: Fetcher instance for RPC calls
        - strip_tz<bool>: strip timezones from datetime values
        - dry_run<bool>: perform sync, but don't actually commit to
            database
    """

    def __init__(self, fetcher, strip_tz=True, dry_run=False, **_):
        self._fetcher = fetcher
        self.strip_tz = strip_tz
        self.dry_run = dry_run
        # allow dep. injection for testing
        self._ContextClass = UpdateContext
        # Must initialize logs now
        _config_logs()
        self._log = logging.getLogger(__name__)

    def update(self, res, pk, depth=1, since=None):
        """
        Try to sync an object to the local database, in case of failure
        where a referenced object is not found, attempt to fetch said
        object from the REST api
        """

        def fetch():
            return self._fetcher.fetch_latest(res, pk, 1, since=since)

        self._update(res, fetch, depth)

    def update_where(self, res, depth=0, since=None, **kwargs):
        "Like update() but uses WHERE-style args"

        def fetch():
            return self._fetcher.fetch_all_latest(res, 0, kwargs, since=since)

        self._update(res, fetch, depth)

    def update_all(self, rs=None, since=None):
        "Sync all objects for the relations rs (if None, sync all resources)"
        self._log.info("Updating resources: %s", " ".join(r.tag for r in (rs or [])))

        if rs is None:
            rs = resource.all_resources()
        ctx = self._ContextClass(self)
        for r in rs:
            with self._transaction():
                ctx.sync_resource(r, since=since)

    def _update(self, res, fetch_func, depth):
        ctx = self._ContextClass(self)
        data, e = fetch_func()
        if e:
            raise e
        self._log.info(f"Updates to be processed: {len(data)}")
        with self._transaction():
            ctx.sync_rows(res, data, depth + 1)

    @contextmanager
    def _transaction(self):
        try:
            with get_backend().atomic_transaction():
                yield
                if self.dry_run:
                    raise _CancelSave
                self._log.debug("Committing transaction")
        except _CancelSave:
            self._log.info("Transaction commit was cancelled (dry run)")


# Holds the state relevant to a single sync
# fetched: contains finished fetch-and-sync jobs
class UpdateContext:
    def __init__(self, updater):
        self.updater = updater
        self.fetcher = updater._fetcher
        self._log = updater._log
        self._jobs = {R: {} for R in resource.all_resources()}, threading.Lock()
        self.disable_partial = True  # TODO
        self.start_time = datetime.utcnow()

    @_tasks.run_task
    def sync_resource(self, res, since=None):
        self._log.info("Fetching & updating all: %s", res.tag)
        data, e = self.fetcher.fetch_all_latest(res, 0, since=since)
        self._log.info("Updates to be processed: %s", len(data))
        return _tasks.gather(self._schedule_rows(res, data, 0))

    # # Disabled, runaway memory
    # def sync_resources(self, rs):
    #     yield _tasks.gather(chain.from_iterable(self.sync_resource(res) for res in rs))

    @_tasks.run_task
    def sync_rows(self, res, rows, depth):
        return _tasks.gather(self._schedule_rows(res, rows, depth))

    def _schedule_rows(self, res, rows, depth):
        return [
            self.set_job((res, row["id"]), self.sync_row, (res, row, depth))
            for row in rows
        ]

    def get_task(self, key):
        """Get a scheduled task, or none"""
        res, pk = key
        jobs, lock = self._jobs
        with lock:
            return jobs[res].get(pk)

    def set_job(self, key, func, args):
        """
        Get a scheduled task or set if none exists.

        Returns:
            - task coroutine/continuation
        """
        res, pk = key
        jobs, lock = self._jobs
        task = _tasks.UpdateTask(func(*args), key)
        with lock:
            job = jobs[res].get(pk)
            had = bool(job)
            if not job:
                job = task
                jobs[res][pk] = job
            else:
                task.cancel()
        self._log.debug(
            "Scheduling: %s-%s (%s)", res.tag, pk, "new task" if not had else "dup"
        )
        return job

    def pending_jobs(self, res):
        "Synchronized access to tasks"
        jobs, lock = self._jobs
        with lock:
            return jobs[res].copy()

    @_tasks.wrap_generator
    def fetch_and_index(self, fetch_func):
        "Fetch data with func, return dict indexed by ID"
        data, e = fetch_func()
        if e:
            raise e
        yield {row["id"]: row for row in data}

    # Update an object after the fetch job finishes
    @_tasks.wrap_generator
    def update_after(self, res, pk, depth, fetch_job):
        data = yield fetch_job
        if data:
            try:
                row = data[pk]
            except KeyError:
                print("Data", data)
                raise
        else:
            self._log.info("Fetched no data for %s-%s", res.tag, pk)
            data, e = self.fetcher.fetch_deleted(res, pk, 0)
            if not data:
                self._log.info(
                    "Fetched no deleted objects for %s-%s, aborting", res.tag, pk
                )
                return
            row = data[0]
        yield self.sync_row(res, row, depth)

    @_tasks.wrap_generator
    def sync_row(self, res, row, depth):
        B = get_backend()

        def _have(R, pks):
            have = B.get_objects(B.get_concrete(R), pks)
            return set(have.values_list("id", flat=True))

        self._log.debug("sync_row(%s, %s, %s)", res.tag, row["id"], depth)
        if self.disable_partial and depth > 0:
            raise ValueError("depth > 0 sync is disabled")

        # Before attempting to set the related-object fields, ensure they are synced
        # Skip all ref'd objects that we already have, or have scheduled to update
        fetched, dangling = _sync.extract_relations(B, res, row)
        sync_jobs = []

        for R, sub in fetched.items():
            have = _have(R, set(sub.keys()))
            sync_jobs.extend(
                self.set_job((R, pk), self.sync_row, (R, subrow, depth - 1))
                for pk, subrow in sub.items()
                if not (pk in have)
            )

        for R, pks in dangling.items():
            pks = pks.difference(_have(R, pks))
            pending = self.pending_jobs(R)
            needpks = []
            for pk in pks:
                if pk in pending:
                    sync_jobs.append(self.get_task((R, pk)))
                else:
                    needpks.append(pk)
            if not needpks:
                continue

            def fetch_dangling(_R=R, _pks=needpks):
                return self.fetcher.fetch_all(_R, 0, dict(id__in=_pks))

            fetch_job = _tasks.UpdateTask(
                self.fetch_and_index(fetch_dangling), (R, None)
            )
            sync_jobs.extend(
                self.set_job((R, pk), self.update_after, (R, pk, depth - 1, fetch_job))
                for pk in pks
            )

        obj = _sync.initialize_object(B, res, row)
        _sync.set_scalars(B, res, obj, row)

        # Resolve refs and then save full object
        self._log.debug(" waiting for: %s", sync_jobs)
        yield _tasks.gather(sync_jobs)
        self._log.debug("sync_row(%s, %s, %s) (resumed)", res.tag, row["id"], depth)

        _sync.set_single_relations(B, res, obj, row)
        # Detect integrity gaps
        dup_fields, missing = _sync.clean_helper(B, obj, B.clean)

        if dup_fields:
            job = self._handle_duplicate(res, obj, dup_fields)
            sync_jobs.append(job)

        # ignore expected missing refs
        for R, pks in missing.items():
            for pk in pks:
                if pk not in dangling[R]:  # shouldn't happen
                    raise RuntimeError("Unexpected missing relation", (R, pk))

        _sync.patch_object(B, res, obj, self.updater.strip_tz)

        # Ignore new objects for consistency - TODO: test
        if obj.updated >= self.start_time:
            self._log.info(
                "Ignoring object updated after sync began: (%s-%s)", res.tag, row["id"]
            )
            return

        # Preliminary save so this object exists for its dependents
        # XXX Doesn't work in MySQL, single-refs must exist
        if not self.updater.dry_run:
            B.save(obj)
            # B.get_objects(res, pk=row['id']).update()

        def finish():
            _sync.set_single_relations(B, res, obj, row)
            _sync.set_many_relations(B, res, obj, row)

            if self.updater.dry_run:
                return
            B.clean(obj)
            B.save(obj)

        self.set_job(
            (res, row["id"]), self.sync_row_finish, (res, row["id"], finish, sync_jobs)
        )

    @_tasks.wrap_generator
    def sync_row_finish(self, res, pk, func, sync_jobs):
        # Resolve refs and then save full object
        self._log.debug(" waiting for: %s", sync_jobs)
        yield _tasks.gather(sync_jobs)
        self._log.debug("sync_row(%s, %s) (finish)", res.tag, pk)
        func()

    def _handle_duplicate(self, res, obj, dup_fields):
        B = get_backend()
        # Try to update conflicting object
        field = dup_fields[0]
        value = getattr(obj, field)
        try:
            dup = B.get_object_by(B.get_concrete(res), field, value)
            dup_id = dup.id
            dup.delete(hard=True)
        except B.object_missing_error(B.get_concrete(res)):  # shouldn't happen
            raise Exception("internal error")

        self._log.debug("dup: %s = %s", field, value)

        def fetch_dup():
            data, err = self.fetcher.fetch_latest(res, dup_id, 0)
            if isinstance(err, _fetch.NotFoundException):
                # case where the local duplicate has been deleted
                return {}, None
            return data, err

        fetch_job = _tasks.UpdateTask(self.fetch_and_index(fetch_dup), (res, dup_id))
        return self.set_job(
            (res, dup_id), self.update_after, (res, dup_id, 0, fetch_job)
        )
