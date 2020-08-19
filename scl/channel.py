from rclpy.qos import QoSProfile
from .impl.singleton import Singleton


class StreamPort(metaclass=Singleton):
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self._namespace = None

    def set_channel(self, channel):
        self._channel = channel

    def set_msg_type(self, msg_type):
        self._msg_type = msg_type

    def set_namespace(self, namespace):
        self._namespace = namespace


class StreamInputPort(StreamPort):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self._data_queue = []

    def attach(self):
        topic = self._namespace + "/" + self._channel if self._namespace else self._channel
        self._subscription = self.parent.create_subscription(
            self._msg_type, topic, self._check_mode_and_execute_callback, 1)

    def set_callback(self, callback):
        self._callback = callback
    
    def set_freshness_constraint(self, freshness_constraint):
        self.freshness_constraint = freshness_constraint

    def _check_mode_and_execute_callback(self, msg):
        if self.parent.mode == self.parent.get_current_mode():
            self._callback(msg)
        else:
            pass

class StreamOutputPort(StreamPort):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        
    def attach(self):
        topic = self._namespace + "/" + self._channel if self._namespace else self._channel
        self._publisher = self.parent.create_publisher(
            self._msg_type, topic, 1)

    def set_rate_constraint(self, rate_constraint):
        self.rate_constraint = rate_constraint

    def write(self, msg):
        self._publisher.publish(msg)
