# Units tests to directly cover both task wrapper modules -
# not possible with pytest parametrization

import sys
from collections import defaultdict

import pytest

from peeringdb import _tasks_sequential

TASKS_MODS = [_tasks_sequential]
# pre-async compat. import
if sys.version_info >= (3, 5):
    from peeringdb import _tasks_async

    TASKS_MODS.append(_tasks_async)

# dummy resources for task objects
class ResOne:
    tag = "one"


class ResTwo:
    tag = "two"


DATA_EXPECTED = {ResOne: [1, 2], ResTwo: [1, 2]}

# dummy context classes parameterized on tasks module
def make_context(tasks):
    class Context:
        def __init__(self):
            self.jobs = defaultdict(dict)
            self.db = {}

        @tasks.run_task
        def do_sync(self, res):
            return tasks.gather(self.schedule(res))

        def schedule(self, res):
            return [self.set_job(res, k) for k in DATA_EXPECTED[res]]

        def set_job(self, res, k):
            job = self.jobs[res].get(k)
            if not job:
                job = tasks.UpdateTask(self._sync_impl(res, k), (res, k))
                self.jobs[res][k] = job
            return job

        @tasks.wrap_generator
        def _sync_impl(self, res, k):
            d = self.db.setdefault(res, [])
            # pretend ResOne has dependency on a ResTwo
            if res is ResOne:
                yield self.set_job(ResTwo, k)
            d.append(k)

    return Context


@pytest.mark.parametrize("tasks_mod", TASKS_MODS)
def test_basic(tasks_mod):
    # generate class
    Context = make_context(tasks_mod)

    # do a dummy sync
    ctx = Context()
    for res in DATA_EXPECTED:
        ctx.do_sync(res)

    assert ctx.db == DATA_EXPECTED
