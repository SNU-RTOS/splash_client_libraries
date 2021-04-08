from rclpy.publisher import Publisher
from rclpy.subscription import Subscription
from std_msgs.msg import String, Header, Time
from splash_interfaces.msg import ModeChange

class StreamInputPort:
    def __init__(self, component, name, msg_type, channel, callback):
        self.component = component
        self.name = name
        self.msg_type = msg_type
        self.channel = channel
        self.callback = callback
        self.subscription = self.component.create_subscription(self.msg_type, self.channel, self._execute_callback, 10)

    def _execute_callback(self, msg_type):
        self.callback(self.component, msg_type)
    
class StreamOutputPort:
    def __init__(self, component, name, msg_type, channel, rate=None):
        self.component = component
        self.name = name
        self.msg_type = msg_type
        self.channel = channel
        self.rate = rate
        self.publisher = self.component.create_publisher(self.msg_type, self.channel, 10)
        
    def write(self, msg):
        self.publisher.publish(msg)

class EventInputPort:
    def __init__(self, component, name, event, callback):
        self.component = component
        self.name = name
        self.event = event
        self.subscription = self.component.create_subscription(String, self.event, self._execute_callback, 10)
        self.callback = callback

    def _execute_callback(self, msg_type):
        self.callback(self,component, msg_type)
    
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
        self.publisher = self.component.create_publisher(String, self.event)

    def trigger(self, event):
        msg = ModeChange()
        header = Header()
        header.stamp = self.component.get_clock().now().to_msg()
        header.frame_id = self.component.name
        msg.header = header
        msg.factory = self.factory
        msg.event = event
        self.publisher.publish(msg)
        
