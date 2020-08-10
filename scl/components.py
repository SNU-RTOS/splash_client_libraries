import json
from rclpy.node import Node
from .channel import StreamInputPort, StreamOutputPort
from .clink import EventInputPort, EventOutputPort, ModeChangeInputPort, ModeChangeOutputPort
from .exceptions import *


class Component(Node):
    def __init__(self, name):
        self.__name = name
        self.__stream_input_ports = {}
        self.__stream_output_ports = {}
        self.__modechange_output_ports = {}
        self.__event_input_ports = {}
        self.__event_output_ports = {}
        self.__info = {
            "factory": "",
            "mode": "",
            "stream_input_ports": [],
            "stream_output_ports": [],
            "event_input_ports": [],
            "event_output_ports": [],
            "modechange_output_ports": [],
            "links": []
        }

    def set_info(self, factory, mode, stream_input_ports, stream_output_ports, event_input_ports, event_output_ports, modechange_output_ports, links):
        self.__info["factory"] = factory
        self.__info["mode"] = mode
        self.__info["stream_input_ports"] = stream_input_ports
        self.__info["stream_output_ports"] = stream_output_ports
        self.__info["event_input_ports"] = event_input_ports
        self.__info["event_output_ports"] = event_output_ports
        self.__info["modechange_output_ports"] = modechange_output_ports
        self.__info["links"] = links
        factory_ = factory.lower().replace(" ", "_")
        factory_ = factory_ + '/' if factory else factory
        mode_ = mode.lower().replace(" ", "_")
        mode = mode_ + '/' if mode else mode
        super().__init__(self.__name, namespace="{}{}".format(factory_, mode_))

    def attach_input_port(self, msg_type, channel, callback):
        links = self.__info["links"]
        for link in links:
            if link["from"]["channel"] == channel:
                factory = link["from"]["parent"]["factory"].lower().replace(
                    " ", "_")
                factory = factory + '/' if factory else factory
                mode = link["from"]["parent"]["mode"].lower().replace(" ", "_")
                mode = mode + '/' if mode else mode
                topic_name = "{}{}{}".format(factory, mode, channel)
                self.__stream_input_ports[channel] = StreamInputPort(
                    self, msg_type, topic_name, callback)
                break

    def attach_output_port(self, msg_type, channel):
        links = self.__info["links"]
        for link in links:
            if link["to"]["channel"] == channel:
                factory = link["to"]["parent"]["factory"].lower().replace(
                    " ", "_")
                factory = factory + '/' if factory else factory
                mode = link["to"]["parent"]["mode"].lower().replace(" ", "_")
                mode = mode + '/' if mode else mode
                topic_name = "{}{}{}".format(factory, mode, channel)
                self.__stream_output_ports[channel] = StreamOutputPort(
                    self, msg_type, topic_name)

    def attach_modechange_output_port(self, mode):
        self.__modechange_output_ports[mode] = ModeChangeOutputPort(self, mode)

    def attach_event_output_port(self, srv, event):
        self.__event_output_ports[event] = EventOutputPort(self, srv, event)

    def attach_event_input_port(self, srv, event, callback):
        self.__event_input_ports[event] = EventInputPort(
            self, srv, event, callback)

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

    def __init__(self):
        super.__init__()
        self.__fusion_rule = None
        self.__queues_for_each_input_port = {}

    def attach_input_port(self, msg_type, channel):
        links = self.__info["links"]
        for link in links:
            if link["from"]["channel"] == channel:
                factory = link["from"]["parent"]["factory"].lower().replace(
                    " ", "_")
                factory = factory + '/' if factory else factory
                mode = link["from"]["parent"]["mode"].lower().replace(" ", "_")
                mode = mode + '/' if mode else mode
                topic_name = "{}{}{}".format(factory, mode, channel)
                self.__stream_input_ports[channel] = StreamInputPort(
                    self, msg_type, topic_name, self.__check_and_fusion)
                self.__queues_for_each_input_port[topic_name] = []
                break

    def attach_input_port(self, msg_type, channel, callback):
        raise AttributeError(
            "'FusionOperator' has no attribute 'attach_input'")

    def attach_output_port(Self, channel):
        links = self.__info["links"]
        for link in links:
            if link["to"]["channel"] == channel:
                factory = link["to"]["parent"]["factory"].lower().replace(
                    " ", "_")
                factory = factory + '/' if factory else factory
                mode = link["to"]["parent"]["mode"].lower().replace(" ", "_")
                mode = mode + '/' if mode else mode
                topic_name = "{}{}{}".format(factory, mode, channel)
                self.__stream_output_ports[channel] = StreamOutputPort(
                    self, msg_type, topic_name)

    def set_fusion_rule(self, m_ports, o_ports, o_ports_threshhold, correlation):
        self.__fusion_rule = FusionRule(
            m_ports, o_ports, o_ports_threshhold, correlation)

    def __check_and_fusion(self, msg, topic_name):
        self.__queues_for_each_input_port[topic_name].append()
        if self.__fusion_rule.check(self.__queues_for_each_input_port):
            data = {length: len(self.__queues_for_each_input_port.keys())}
            for key, value in self.__queues_for_each_input_port.items():
                data[key] = value.pop(0)
            data_encoded = json.dumps(data)
            for stream_output_port in self.__stream_output_ports:
                stream_output_port.write(msg)
        else:
            pass
