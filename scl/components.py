from rclpy.node import Node
from .port import StreamInputPort, StreamOutputPort

from typing import Callable



class Component(Node):
    def __init__(self, name):
        super().__init__(name)
        self.stream_input_ports = {}
        self.stream_output_ports = {}
        self.event_input_ports = {}
        self.event_output_ports = {}
        self.mode_change_ports = {}

    def create_and_attach_stream_input_port(
        self,  
        name: str,
        msg_type,
        channel: str,
        callback: Callable[[Component, MsgType], None]
    ):
        self.callback = callback
        self.stream_input_ports[channel] = StreamInputPort(self, name, msg_type, channel, callback)
        
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
        callback: Callable[[Component, MsgType], None]
    ):
        self.event_input_ports[event] = EventInputPort(self, name, event)
    
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
        event: str
    ):
        self.mode_change_ports[factory] = ModeChangePort(self, name, factory, event)

    def write(self, channel, msg):
        self.stream_output_ports[channel].write(msg)

    def trigger_event(self, event):
        self.event_output_ports[event].trigger()

    def trigger_modechange(self, factory, event):
        self.mode_change_ports[factory].trigger(event)
    

class ProcessingComponent(Component):
    def __init__(self, name):
        super().__init__(name)

class SourceComponent(Component):
    def __init__(self, name):
        super().__init__(name)

class SinkComponent(Component):
    def __init__(self, name):
        super().__init__(name)

class FusionOpertaor(Component):
    def __init__(self, name):
        super().__init__(name)
    