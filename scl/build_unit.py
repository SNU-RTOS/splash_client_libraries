from .impl.singleton import Singleton
import rclpy
from rclpy.executors import MultiThreadedExecutor


class BuildUnit(metaclass=Singleton):
    def __init__(self):
        self.context = rclpy.init()
        self.executor = MultiThreadedExecutor()
        self.components = []

    def run(self):
        for component in self.components:
            self.executor.add_node(component)
            component.run()
        try:
            self.executor.spin()
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            for component in self.components:
                component.destroy_node()
            self.executor.shutdown()
            