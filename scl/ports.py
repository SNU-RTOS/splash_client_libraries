from rclpy.publisher import Publisher
from rclpy.subscription import Subscription
from rclpy.time import Time

from std_msgs.msg import String, Header
from splash_interfaces.msg import SplashMessage, ModeChange
from srl.rate_control import RateController

import pickle
import time
class StreamInputPort:
    def __init__(self, component, name, msg_type, channel, callback):
        self.component = component
        self.name = name
        self.msg_type = msg_type
        self.channel = channel
        self.callback = callback
        self.subscription = self.component.create_subscription(SplashMessage, self.channel, self._execute_callback, 10, callback_group=self.component.callback_group)
        self.msg_list = []
    
    def _execute_callback(self, msg):
        self.msg_list.append(msg)
        self.callback(self.channel, msg)
        self.msg_list.pop(0)
        
    
class StreamOutputPort:
    def __init__(self, component, name, msg_type, channel, rate=None):
        self.component = component
        self.name = name
        self.msg_type = msg_type
        self.channel = channel
        self.rate = rate
        self.publisher = self.component.create_publisher(SplashMessage, self.channel, 10)
        if self.rate:
            self.rate_controller = RateController(self)
    def write(self, msg):
        if self.rate:
            self.rate_controller.push(msg)
        else:
            time_exec_ms = (self.component.get_clock().now().nanoseconds - Time.from_msg(msg.header.stamp).nanoseconds) / 1000000
            if msg.freshness_constraint == 0 or time_exec_ms < msg.freshness_constraint:
                self.publisher.publish(msg)

class EventInputPort:
    def __init__(self, component, name, event, callback):
        self.component = component
        self.name = name
        self.event = event
        self.subscription = self.component.create_subscription(String, self.event, self._execute_callback, 10, callback_group=self.component.callback_group)
        self.callback = callback

    def _execute_callback(self, msg):
        self.callback(self.component, msg)
    
class EventOutputPort:
    def __init__(self, component, name, event):
        self.component = component
        self.name = name
        self.event = event
        self.publisher = self.component.create_publisher(String, self.event, 10)

    def trigger(self):
        msg = String()
        self.publisher.publish(msg)
    
class ModeChangePort:
    def __init__(self, component, name, factory):
        self.component = component
        self.name = name
        self.factory = factory
        self.publisher = self.component.create_publisher(ModeChange, 'splash_modechange', 10)

    def trigger(self, event):
        msg = ModeChange()
        header = Header()
        header.stamp = self.component.get_clock().now().to_msg()
        header.frame_id = self.component.name
        msg.header = header
        msg.factory = self.factory
        msg.event = event
        self.publisher.publish(msg)
        
