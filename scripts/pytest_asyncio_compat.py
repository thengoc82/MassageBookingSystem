"""Small pytest 9 runner for this repo's coroutine tests.

The installed pytest-asyncio 0.21 plugin predates pytest 9. Load this plugin
explicitly with ``-p no:asyncio -p scripts.pytest_asyncio_compat`` until the
test dependency versions are aligned.
"""

import asyncio
import inspect

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        names = pyfuncitem._fixtureinfo.argnames
        asyncio.run(pyfuncitem.obj(**{name: pyfuncitem.funcargs[name] for name in names}))
        return True
    return None
