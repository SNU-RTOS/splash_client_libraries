from .impl.singleton import Singleton
import rclpy
from rclpy.executors import MultiThreadedExecutor
import sys
sys.path.append("C:/Workspace/rtos/Splash/RuntimeLibraries")
import srl

class BuildUnit(Singleton):
    def __init__(self):
        self.context = rclpy.init()
        self.executor = MultiThreadedExecutor()
        self.components = []

    def connect(self, ip, port, authkey):
        self.client_manager = srl.make_client_manager(ip, port, authkey)
        self.mode = client_manager.get_mode()

    def _work(self):
        for component in self.components:
            executor.add_node(component)
            component.run()
        executor.spin()

    def run(self):
        srl.start(self._work, args=(self.mode))
    
    def __del__(self):
        rclpy.shutdown()