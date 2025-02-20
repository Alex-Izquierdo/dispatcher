import asyncio
import multiprocessing
from typing import Callable, Iterable, Optional, Union

from dispatcher.worker.task import work_loop


class ProcessProxy:
    def __init__(self, args: Iterable, finished_queue: multiprocessing.Queue, target: Callable = work_loop) -> None:
        self.message_queue: multiprocessing.Queue = multiprocessing.Queue()
        self._process = multiprocessing.Process(target=target, args=tuple(args) + (self.message_queue, finished_queue))

    def start(self) -> None:
        self._process.start()

    def join(self, timeout: Optional[int] = None) -> None:
        if timeout:
            self._process.join(timeout=timeout)
        else:
            self._process.join()

    @property
    def pid(self) -> Optional[int]:
        return self._process.pid

    def exitcode(self) -> Optional[int]:
        return self._process.exitcode

    def is_alive(self) -> bool:
        return self._process.is_alive()

    def kill(self) -> None:
        self._process.kill()

    def terminate(self) -> None:
        self._process.terminate()


class ProcessManager:
    def __init__(self) -> None:
        self.finished_queue: multiprocessing.Queue = multiprocessing.Queue()
        self._loop = None

    def get_event_loop(self):
        if not self._loop:
            self._loop = asyncio.get_event_loop()
        return self._loop

    def create_process(self, args: Iterable[int | str | dict], **kwargs) -> ProcessProxy:
        return ProcessProxy(args, self.finished_queue, **kwargs)

    async def read_finished(self) -> dict[str, Union[str, int]]:
        message = await self.get_event_loop().run_in_executor(None, self.finished_queue.get)
        return message
