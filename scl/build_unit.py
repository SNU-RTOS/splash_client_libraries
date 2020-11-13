from .impl.singleton import Singleton
from .exceptions import ModeManagerAbsenceException, InvalidModeChangeException
from .executor import SplashExecutor

import rclpy

from rclpy.node import Node
from std_srvs.srv import Empty

class BuildUnit(metaclass=Singleton):
    class ModeManagerChecker(Node):
        def __init__(self):
            super().__init__("mode_manager_alive_checker")
            self._cli = self.create_client(Empty, '/check_alive_mode_manager')
            self._req = Empty.Request()
            while not self._cli.wait_for_service(timeout_sec=1.0):
                self.get_logger().error("Please run splash server. waiting for 1 second...")
            self.create_timer(1, self._check_alive_mode_manager)
            self.absence = False
        def _check_alive_mode_manager(self):
            if not self._cli.wait_for_service(timeout_sec=1.0):
                self.absence = True

    def __init__(self):
        self.context = rclpy.init()
        self.executor = SplashExecutor()
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
                    self.modeManagerChecker.get_logger().error("Splash server is not running. Please rerun splash server")
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            for component in self.components:
                component.destroy_node()
            self.executor.shutdown()
