from rclpy.service import Service
from std_msgs.msg import String
from std_srvs.srv import Trigger
from splash_interfaces.srv import RegisterMode, RequestModeChange
import json
class ModeChangeInputPort:
    def __init__(self, component):
        self._component = component
        
        self._request_register_mode()
        
        self._subsription = self._component.create_subscription(String, "splash_mode_change_{}".format(component.factory.name), self._mode_change_callback, 1)

    def _mode_change_callback(self, msg):
        if self._component.get_current_mode() != msg.data:
            self._component.set_current_mode(msg.data)
        else:
            pass

    def _request_register_mode(self):
        _cli = self._component.create_client(RegisterMode, '/register_splash_mode')
        while not _cli.wait_for_service(timeout_sec=1.0):
            self._component.get_logger().info('service not available, waiting again...')
        _req = RegisterMode.Request()
        _req.name_space = self._component.get_namespace()
        _req.factory = self._component.factory.name
        _req.mode_configuration = json.dumps(self._component.factory.mode_configuration)
        future = _cli.call_async(_req)
        
        
        

class ModeChangeOutputPort:
    def __init__(self, component, event):
        self._component = component
        self._event = event
        self._client = self._component.create_client(event)


class EventInputPort:
    def __init__(self, component, event, callback):
        self._component = component
        self._event = event
        self._callback = callback
        self._service = self._component.create_service(Trigger, event, self._check_mode_and_execute_callback)
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