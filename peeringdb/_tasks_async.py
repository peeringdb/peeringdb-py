"""
Wrapper module for asynchronous task handling.
"""
import asyncio, inspect


class UpdateTask(asyncio.Task):
    """Wrap a coroutine in a future"""

    def __init__(self, coro, desc, loop=None):
        """
        Arguments:
            - coro: awaitable object
            - desc<tuple>: (Resource, key)
        """
        assert asyncio.iscoroutine(coro), coro
        self._desc = desc
        super().__init__(coro)

    def __repr__(self):
        res, pk = self._desc
        return "<UpdateTask for ({}, {})>".format(res.tag, pk)


def gather(jobs):
    "Aggregate and collect jobs"
    return asyncio.gather(*jobs, return_exceptions=False)


def wrap_generator(func):
    """
    Decorator to convert a generator function to an async function which collects
    and returns generator results, returning a list if there are multiple results
    """

    async def _wrapped(*a, **k):
        r, ret = None, []
        gen = func(*a, **k)
        while True:
            try:
                item = gen.send(r)
            except StopIteration:
                break
            if inspect.isawaitable(item):
                r = await item
            else:
                r = item
            ret.append(r)

        if len(ret) == 1:
            return ret.pop()
        return ret

    return _wrapped


def run_task(func):
    """
    Decorator to wrap an async function in an event loop.
    Use for main sync interface methods.
    """

    def _wrapped(*a, **k):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*a, **k))

    return _wrapped
