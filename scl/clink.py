from rclpy.service import Service
from std_msgs.msg import String

class ModeChangeInputPort:
    def __init__(self, component, mode):
        self._component = component
        self._subsription = self._component.create_subscription(String, "splash_mode_change_{}".format(component.factory.name), self._mode_change_callback, 1)
    def _mode_change_callback(self, msg):
        if self._component.mode != msg.data:
            self._component.set_current_mode(msg.data)
        else:
            pass


class ModeChangeOutputPort:
    def __init__(self, component, event):
        self._component = component
        self._event = event


class EventInputPort:
    def __init__(self, component, srv, event, callback):
        self._component = component
        self._event = event
        self._callback = callback
        self._service = self._component.create_service(srv, event, self._check_mode_and_execute_callback)
    def _check_mode_and_execute_callback(self, msg):
        if self._component.mode == self._component.get_current_mode():
            self._callback(msg)
        else:
            pass

class EventOutputPort:
    def __init__(self, component, srv, event):
        self._component = component
        self._event = event
        self._client = self._component.create_client(srv, event)