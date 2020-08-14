import json
from rclpy.node import Node
from std_msgs.msg import String
from .channel import StreamInputPort, StreamOutputPort
from .clink import EventInputPort, EventOutputPort, ModeChangeOutputPort
from .impl.singleton import Singleton
from .exceptions import *
import srl

class Component(Singleton, Node):
    def __init__(self, name, factory, mode):
        self.name = name
        self.factory = factory
        self.mode = mode
        self._stream_input_ports = {}
        self._stream_output_ports = {}
        self._event_input_ports = {}
        self.ros_context = None
        namespace = factory.get_namespace() if factory else ""
        self._namespace = namespace + '/' + \
            mode.lower().replace(" ", "_") if mode else namespace
    
    def set_context(self, context):
        self.ros_context = context

    def set_links(self, links):
        self.links = links
        super().__init__(self.name, context=self.ros_context, namespace=self._namespace)

    def get_namespace(self):
        return self._namespace

    def attach_stream_input_port(self, msg_type, channel, callback):
        for link in self.links:
            if link.channel == channel:
                port = link.dst
                port.set_msg_type(msg_type)
                port.set_channel(channel)
                port.set_callback(callback)
                port.set_namespace(link.src.parent.get_namespace())
                port.attach()
                self._stream_input_ports[channel] = port
                break

    def attach_stream_output_port(self, msg_type, channel):
        for link in self.links:
            if link.channel == channel:
                port = link.src
                port.set_msg_type(msg_type)
                port.set_channel(channel)
                port.set_namespace(link.dst.parent.get_namespace())
                port.attach()
                self._stream_output_ports[channel] = port
                break

    def attach_modechange_output_port(self, mode):
        pass

    def attach_event_output_port(self, srv, event):
        pass

    def attach_event_input_port(self, srv, event, callback):
        self._event_input_ports[event] = EventInputPort(
            self, srv, event, callback)

    def get_stream_output_port(self, channel):
        return self._stream_output_ports[channel]

    def setup(self):
        pass

    def run(self):
        pass

class FusionOperator(Component):
    class FusionRule():
        def __init__(self, m_ports, o_ports, o_ports_threshhold, correlation):
            self.mandatory_ports = m_ports
            self.optional_ports = o_ports
            self.optional_ports_threshold = o_ports_threshhold
            self.correlation = correlation

        def check(self, queues_for_each_input_port):
            return True

    def __init__(self, name, factory, mode):
        super().__init__(name, factory, mode)
        self._fusion_rule = None
        self._queues_for_each_input_port = {}

    def attach_stream_input_port(self, msg_type, channel):
        for link in self.links:
            if link.channel == channel:
                port = link.dst
                port.set_msg_type(msg_type)
                port.set_channel(channel)
                port.set_callback(self._check_and_fusion)
                port.set_namespace(link.src.parent.get_namespace())
                port.attach()
                self._stream_input_ports[channel] = port
                break

    def attach_stream_output_port(self, channel):
        for link in self.links:
            if link.channel == channel:
                port = link.src
                port.set_msg_type(String)
                port.set_channel(channel)
                port.set_namespace(link.dst.parent.get_namespace())
                port.attach()
                self._stream_output_ports[channel] = port
                break

    def set_fusion_rule(self, fusion_rule):
        m_ports = fusion_rule["mandatory_ports"]
        o_ports = fusion_rule["optional_ports"]
        o_ports_threshhold = fusion_rule["optional_ports_threshold"]
        correlation = fusion_rule["correlation"]
        self._set_fusion_rule(m_ports, o_ports,
                              o_ports_threshhold, correlation)

    def _set_fusion_rule(self, m_ports, o_ports, o_ports_threshhold, correlation):
        self._fusion_rule = self.FusionRule(
            m_ports, o_ports, o_ports_threshhold, correlation)

    def _check_and_fusion(self, msg, topic_name):
        print("check_and_fusion")
        self._queues_for_each_input_port[topic_name].append()
        if self._fusion_rule.check(self._queues_for_each_input_port):
            data = {length: len(self._queues_for_each_input_port.keys())}
            for key, value in self._queues_for_each_input_port.items():
                data[key] = value.pop(0)
            data_encoded = json.dumps(data)
            for stream_output_port in self.__stream_output_ports:
                stream_output_port.write(msg)
        else:
            pass
