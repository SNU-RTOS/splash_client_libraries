import json, time
from rclpy.node import Node
from std_msgs.msg import String
from .channel import StreamInputPort, StreamOutputPort
from .clink import EventInputPort, EventOutputPort, ModeChangeInputPort, ModeChangeOutputPort
from .exceptions import *
from .impl.msg_converter import convert_ros_message_to_dictionary
class Component(Node):
    def __init__(self, name, factory, mode):
        self.name = name
        self.factory = factory
        self.mode = mode
        self._current_mode = None
        self._stream_input_ports = {}
        self._stream_output_ports = {}
        self._mode_input_port = None
        self._event_input_ports = {}
        self.build_unit = None
        namespace = factory.get_namespace() if factory else ""
        self._namespace = namespace + '/' + \
            mode.lower().replace(" ", "_") if mode else namespace

    def set_current_mode(self, mode):
        self._current_mode = mode

    def get_current_mode(self):
        return self._current_mode

    def set_build_unit(self, build_unit):
        self.build_unit = build_unit
        self._create_node()
        if self.factory and self.factory.mode_configuration:
            self.set_current_mode(self.factory.mode_configuration["initial_mode"])
            self.attach_modechange_input_port()

    def _create_node(self):
        super().__init__(self.name, context=self.build_unit.context, namespace=self._namespace)
        
        
    def set_links(self, links):
        self.links = links

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
                if not channel in self._stream_input_ports.keys():
                    self._stream_input_ports[channel] = []
                self._stream_input_ports[channel].append(port)

    def attach_stream_output_port(self, msg_type, channel):
        for link in self.links:
            if link.channel == channel:
                port = link.src
                port.set_msg_type(msg_type)
                port.set_channel(channel)
                port.set_namespace(link.dst.parent.get_namespace())
                port.attach()
                if not channel in self._stream_output_ports.keys():
                    self._stream_output_ports[channel] = []
                self._stream_output_ports[channel].append(port)
            
    def attach_modechange_input_port(self):
        mode_info = next((item for item in self.factory.mode_configuration["mode_list"] if item["name"] == self.mode), None)
        if mode_info:
            self.mode_input_port = ModeChangeInputPort(self)
        
    def attach_modechange_output_port(self, mode):
        pass

    def attach_event_output_port(self, srv, event):
        pass

    def attach_event_input_port(self, event, callback):
        self._event_input_ports[event] = EventInputPort(
            self, event, callback)

    def write(self, channel, msg):
        for port in self._stream_output_ports[channel]:
            port.write(msg)

    def trigger_event(self, event):
        pass

    def trigger_modechange(self, event):
        pass

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
        self._stream_output_ports = []
    def attach_stream_input_port(self, msg_type, channel):
        for link in self.links:
            if link.channel == channel:
                port = link.dst
                port.set_msg_type(msg_type)
                port.set_channel(channel)
                port.set_callback(self._check_and_fusion, (channel,))
                port.set_namespace(link.src.parent.get_namespace())
                port.attach()
                if not channel in self._stream_input_ports.keys():
                    self._stream_input_ports[channel] = []
                self._stream_input_ports[channel].append(port)

    def attach_stream_output_port(self, channel):
        for link in self.links:
            if link.channel == channel:
                port = link.src
                port.set_msg_type(String)
                port.set_channel(channel)
                port.set_namespace(link.dst.parent.get_namespace())
                port.attach()
                self._stream_output_ports.append(port)

    def set_fusion_rule(self, fusion_rule):
        m_ports = self._get_ports_from_key(fusion_rule["mandatory_ports"])
        o_ports = self._get_ports_from_key(fusion_rule["optional_ports"])
        o_ports_threshhold = fusion_rule["optional_ports_threshold"]
        correlation = fusion_rule["correlation"]
        self._set_fusion_rule(m_ports, o_ports,
                              o_ports_threshhold, correlation)
    def _get_ports_from_key(self, ports):
        new_ports = []
        for port in ports:
            port = port.lower().replace(" ", "_")
            for link in self.links:
                if link.dst.name == port:
                    new_ports.append(link.dst)
        return new_ports
    def _set_fusion_rule(self, m_ports, o_ports, o_ports_threshhold, correlation):
        self._fusion_rule = self.FusionRule(
            m_ports, o_ports, o_ports_threshhold, correlation)
    
    def _check_and_fusion(self, msg, channel):
        print("check_and_fusion")
        if not channel in self._queues_for_each_input_port.keys():
            self._queues_for_each_input_port[channel] = []
        self._queues_for_each_input_port[channel].append({"message": msg, "time": time.time()})
        if self._fusion_rule.check(self._queues_for_each_input_port):
            data = {"length": len(self._queues_for_each_input_port.keys())}
            for key, value in self._queues_for_each_input_port.items():
                data[key] = convert_ros_message_to_dictionary(value.pop(0)["message"])
                
            print(data)
            data_encoded = json.dumps(data)
            new_msg = String()
            new_msg.data = data_encoded
            for port in self._stream_output_ports:
                port.write(new_msg)
        else:
            pass
