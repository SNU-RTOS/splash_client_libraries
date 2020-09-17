from .impl.singleton import Singleton
from .exceptions import ModeManagerAbsenceException, InvalidModeChangeException
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import Empty

class BuildUnit(metaclass=Singleton):
    class ModeManagerChecker(Node):
        def __init__(self):
            super().__init__("mode_manager_alive_checker")
            self._cli = self.create_client(Empty, '/check_alive_mode_manager')
            self._req = Empty.Request()
            while not self._cli.wait_for_service(timeout_sec=1.0):
                raise ModeManagerAbsenceException("Please run splash server")
            self.create_timer(1, self._check_alive_mode_manager)
            self.absence = False
        def _check_alive_mode_manager(self):
            if not self._cli.wait_for_service(timeout_sec=1.0):
                self.absence = True

    def __init__(self):
        self.context = rclpy.init()
        self.executor = MultiThreadedExecutor()
        self.components = []
        self.modeManagerChecker = self.ModeManagerChecker()
        self.executor.add_node(self.modeManagerChecker)

    def run(self):
        for component in self.components:
            self.executor.add_node(component)
            component.run()
        try:
            while rclpy.ok():
                self.executor.spin_once()
                if self.modeManagerChecker.absence:
                    raise ModeManagerAbsenceException("Please rerun splash server")
                for component in self.components:
                    if len(component.exceptions) > 0:
                        raise component.exceptions.pop(0)
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            for component in self.components:
                component.destroy_node()
            self.executor.shutdown()
