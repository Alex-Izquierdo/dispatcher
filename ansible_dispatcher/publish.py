import logging
from typing import Optional

from ansible_dispatcher.registry import DispatcherMethodRegistry
from ansible_dispatcher.registry import registry as default_registry
from ansible_dispatcher.utils import DispatcherCallable

logger = logging.getLogger('awx.main.dispatch')


class DispatcherDecorator:
    def __init__(self, registry: DispatcherMethodRegistry, *, queue: Optional[str] = None, on_duplicate: Optional[str] = None) -> None:
        self.registry = registry
        self.queue = queue
        self.on_duplicate = on_duplicate

    def __call__(self, fn: DispatcherCallable, /) -> DispatcherCallable:
        "Concrete task decorator, registers method and glues on some methods from the registry"

        dmethod = self.registry.register(fn, queue=self.queue, on_duplicate=self.on_duplicate)

        setattr(fn, 'apply_async', dmethod.apply_async)
        setattr(fn, 'delay', dmethod.delay)

        return fn


def task(
    *,
    queue: Optional[str] = None,
    on_duplicate: Optional[str] = None,
    registry: DispatcherMethodRegistry = default_registry,
) -> DispatcherDecorator:
    """
    Used to decorate a function or class so that it can be run asynchronously
    via the task dispatcher.  Tasks can be simple functions:

    @task()
    def add(a, b):
        return a + b

    ...or classes that define a `run` method:

    @task()
    class Adder:
        def run(self, a, b):
            return a + b

    # Tasks can be run synchronously...
    assert add(1, 1) == 2
    assert Adder().run(1, 1) == 2

    # ...or published to a queue:
    add.apply_async([1, 1])
    Adder.apply_async([1, 1])

    # Tasks can also define a specific target queue or use the special fan-out queue tower_broadcast:

    @task(queue='slow-tasks')
    def snooze():
        time.sleep(10)

    @task(queue='tower_broadcast')
    def announce():
        print("Run this everywhere!")

    # The registry kwarg changes where the registration is saved, mainly for testing
    # The on_duplicate kwarg controls behavior when multiple instances of the task running
    # options are documented in dispatcher.utils.DuplicateBehavior
    """
    return DispatcherDecorator(registry, queue=queue, on_duplicate=on_duplicate)
