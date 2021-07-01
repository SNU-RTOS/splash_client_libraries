from rclpy.node import Node
from rclpy.time import Time
from .ports import StreamInputPort, StreamOutputPort, EventInputPort, EventOutputPort, ModeChangePort
from std_msgs.msg import String, Header
from splash_interfaces.msg import SplashMessage
from srl.sensor_fusion import FusionRule, SensorFusion
from rclpy.callback_groups import ReentrantCallbackGroup

from typing import Callable
from array import *

import inspect
import pickle
import time

class Component(Node):
    def __init__(self, name, factory=None):
        super().__init__(name)
        self.name = name
        self.factory = factory
        self.stream_input_ports = {}
        self.stream_output_ports = {}
        self.event_input_ports = {}
        self.event_output_ports = {}
        self.mode_change_ports = {}
        self.callbacks = {}
        self.freshness_constraint = 0
        self.is_active = True
        self.callback_group = ReentrantCallbackGroup()
        
    def activate(self):
        self.is_active = True

    def deactivate(self):
        self.is_active = False

class ProcessingComponent(Component):
    def __init__(self, name, factory=None):
        super().__init__(name, factory)
        
    def create_and_attach_stream_input_port(
        self,  
        name: str,
        msg_type,
        channel: str,
        callback
    ):
        self.callbacks[channel] = callback
        self.stream_input_ports[channel] = StreamInputPort(self, name, msg_type, channel, self._data_callback)

    def _data_callback(self, channel, msg):
        deserialized_data = pickle.loads(msg.body)
        self.callbacks[channel](self, deserialized_data)
        
    def create_and_attach_stream_output_port(
        self,
        name: str,
        msg_type,
        channel: str,
        rate=None
    ):
        self.stream_output_ports[channel] = StreamOutputPort(self, name, msg_type, channel, rate)
    
    def create_and_attach_event_input_port(
        self,
        name: str,
        event: str,
        callback
    ):
        self.event_input_ports[event] = EventInputPort(self, name, event, callback)
    
    def create_and_attach_event_output_port(
        self,
        name: str,
        event: str
    ):
        self.event_output_ports[event] = EventOutputPort(self, name, event)

    def create_and_attach_mode_change_port(
        self,
        name: str,
        factory: str,
    ):
        self.mode_change_ports[factory] = ModeChangePort(self, name, factory)

    def write(self, channel, msg):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        caller_name = calframe[1][3]
        source_msg = None

        port = self.stream_output_ports[channel]

        if hasattr(port, 'callback') and caller_name == port.callback.__name__:
            source_msg = port.msg_list[0]

        splash_msg = SplashMessage()

        if source_msg:
            splash_msg.header = source_msg.header
            splash_msg.freshness_constraint = source_msg.freshness_constraint
        else:
            header = Header()
            header.stamp = self.get_clock().now().to_msg()
            header.frame_id = self.name
            splash_msg.header = header
            splash_msg.freshness_constraint = self.freshness_constraint

        serialized_data = array('B', pickle.dumps(msg))
        splash_msg.body = serialized_data

        port.write(splash_msg)

    def trigger_event(self, event):
        self.event_output_ports[event].trigger()

    def trigger_modechange(self, factory, event):
        self.mode_change_ports[factory].trigger(event)
    
class SourceComponent(Component):
    def __init__(self, name, factory=None, freshness_constraint=0):
        super().__init__(name, factory)
        self.freshness_constraint = freshness_constraint

    def create_and_attach_stream_output_port(
        self,
        name: str,
        msg_type,
        channel: str,
        rate=None
    ):
        self.stream_output_ports[channel] = StreamOutputPort(self, name, msg_type, channel, rate)
    
    def write(self, channel, msg):
        port = self.stream_output_ports[channel] 
        serialized_data = array('B', pickle.dumps(msg))
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self.name
        splash_msg = SplashMessage()
        splash_msg.header = header
        splash_msg.body = serialized_data
        splash_msg.freshness_constraint = self.freshness_constraint
        port.write(splash_msg)

class SinkComponent(Component):
    def __init__(self, name, factory=None):
        super().__init__(name, factory)

    def create_and_attach_stream_input_port(
        self,  
        name: str,
        msg_type,
        channel: str,
        callback
    ):
        self.callbacks[channel] = callback
        self.stream_input_ports[channel] = StreamInputPort(self, name, msg_type, channel, self._data_callback)
    
    def _data_callback(self, channel, msg):
        deserialized_data = pickle.loads(msg.body)
        self.callbacks[channel](self, deserialized_data)
    
class FusionOperator(Component):

    def __init__(self, name, factory=None):
        super().__init__(name, factory)
        self.fusion_rule = None
        self.queues_for_input_ports = {}
        sensor_fusion = SensorFusion(self)
        self._fusion_callback = sensor_fusion.fusion_callback
    
    def create_and_attach_stream_input_port(
        self,  
        name: str,
        msg_type,
        channel: str,
    ):
        self.stream_input_ports[channel] = StreamInputPort(self, name, msg_type, channel, self._fusion_callback)

    def create_and_attach_stream_output_port(
        self,
        name: str,
        channel: str,
        rate=None
    ):
        self.output_channel = channel
        self.stream_output_ports[channel] = StreamOutputPort(self, name, String, channel, rate)

    def set_fusion_rule(
        self, 
        mandatory_ports, 
        optional_ports,
        optional_ports_threshold,
        correlation_constraint
    ):
        mandatory_port_objs = []
        optional_port_objs = []
        for mport in mandatory_ports:
            for port in self.stream_input_ports.values():
                if(port.name == mport):
                    mandatory_port_objs.append(port)
                    break
        for oport in optional_ports:
            for port in self.stream_input_ports.values():
                if(port.name == oport):
                    optional_port_objs.append(port)
                    break
        self.fusion_rule = FusionRule(mandatory_port_objs, optional_port_objs, optional_ports_threshold, correlation_constraint)

        for channel in self.stream_input_ports.keys():
            self.queues_for_input_ports[channel] = []

    
