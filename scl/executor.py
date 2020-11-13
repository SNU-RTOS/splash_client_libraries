from rclpy.executors import Executor, ExternalShutdownException, ShutdownException, TimeoutException
from rclpy.context import Context
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

class SplashExecutor(Executor):
    def __init__(self, num_threads: int = None, *, context: Context = None) -> None:
        super().__init__(context=context)
        if num_threads is None:
            try:
                num_threads = multiprocessing.cpu_count()
            except NotImplementedError:
                num_threads = 1
        self._executor = ThreadPoolExecutor(num_threads)
    
    def spin_once(self, timeout_sec: float = None) -> None:
        try:
            handler, entity, node = self.wait_for_ready_callbacks(timeout_sec=timeout_sec)
        except ExternalShutdownException:
            pass
        except ShutdownException:
            pass
        except TimeoutException:
            pass
        else:
            # handler()
            # if handler.exception() is not None:
            #     raise handler.exception()
            self._executor.submit(handler)