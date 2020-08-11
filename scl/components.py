import json
from rclpy.node import Node
from std_msgs.msg import String
from .channel import StreamInputPort, StreamOutputPort
from .clink import EventInputPort, EventOutputPort, ModeChangeOutputPort
from .exceptions import *


class Component(Node):
    def __init__(self, name):
        self._name = name
        self._stream_input_ports = {}
        self._stream_output_ports = {}
        self._modechange_output_ports = {}
        self._event_input_ports = {}
        self._event_output_ports = {}
        self._info = {
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
        self._info["factory"] = factory
        self._info["mode"] = mode
        self._info["stream_input_ports"] = stream_input_ports
        self._info["stream_output_ports"] = stream_output_ports
        self._info["event_input_ports"] = event_input_ports
        self._info["event_output_ports"] = event_output_ports
        self._info["modechange_output_ports"] = modechange_output_ports
        self._info["links"] = links
        factory_ = factory.name.lower().replace(" ", "_") if factory else None
        factory_ = factory_ + '/' if factory else ""
        mode_ = mode.lower().replace(" ", "_")
        mode = mode_ + '/' if mode else mode
        super().__init__(self._name, namespace="{}{}".format(factory_, mode_))

    def attach_stream_input_port(self, msg_type, channel, callback):
        links = self._info["links"]
        for link in links:
            if link["from"]["channel"] == channel:

                factory = link["from"]["parent"]["factory"].lower().replace(
                    " ", "_")
                factory = factory + '/' if factory else factory
                mode = link["from"]["parent"]["mode"].lower().replace(" ", "_")
                mode = mode + '/' if mode else mode
                topic_name = "{}{}{}".format(factory, mode, channel)
                self._stream_input_ports[channel] = StreamInputPort(
                    self, msg_type, topic_name, callback)
                break

    def attach_stream_output_port(self, msg_type, channel):
        links = self._info["links"]
        for link in links:
            if link["to"]["channel"] == channel:
                factory = link["to"]["parent"]["factory"].lower().replace(
                    " ", "_")
                factory = factory + '/' if factory else factory
                mode = link["to"]["parent"]["mode"].lower().replace(" ", "_")
                mode = mode + '/' if mode else mode
                topic_name = "{}{}{}".format(factory, mode, channel)
                self._stream_output_ports[channel] = StreamOutputPort(
                    self, msg_type, topic_name)

    def attach_modechange_output_port(self, mode):
        self._modechange_output_ports[mode] = ModeChangeOutputPort(self, mode)

    def attach_event_output_port(self, srv, event):
        self._event_output_ports[event] = EventOutputPort(self, srv, event)

    def attach_event_input_port(self, srv, event, callback):
        self._event_input_ports[event] = EventInputPort(
            self, srv, event, callback)

    def get_stream_output_port(channel):
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

    def __init__(self, name):
        super().__init__(name)
        self._fusion_rule = None
        self._queues_for_each_input_port = {}

    def attach_stream_input_port(self, msg_type, channel):
        links = self._info["links"]
        for link in links:
            if link["from"]["channel"] == channel:
                factory = link["from"]["parent"]["factory"].lower().replace(
                    " ", "_")
                factory = factory + '/' if factory else factory
                mode = link["from"]["parent"]["mode"].lower().replace(" ", "_")
                mode = mode + '/' if mode else mode
                topic_name = "{}{}{}".format(factory, mode, channel)
                self._stream_input_ports[channel] = StreamInputPort(
                    self, msg_type, topic_name, self._check_and_fusion)
                self._queues_for_each_input_port[topic_name] = []
                break

    def attach_stream_output_port(self, channel):
        links = self._info["links"]
        for link in links:
            if link["to"]["channel"] == channel:
                factory = link["to"]["parent"]["factory"].lower().replace(
                    " ", "_")
                factory = factory + '/' if factory else factory
                mode = link["to"]["parent"]["mode"].lower().replace(" ", "_")
                mode = mode + '/' if mode else mode
                topic_name = "{}{}{}".format(factory, mode, channel)
                self._stream_output_ports[channel] = StreamOutputPort(
                    self, String, topic_name)

    def set_info(self, factory, mode, stream_input_ports, stream_output_ports, event_input_ports, event_output_ports, modechange_output_ports, links, fusion_rule):
        super().set_info(factory, mode, stream_input_ports, stream_output_ports,
                         event_input_ports, event_output_ports, modechange_output_ports, links)
        m_ports = fusion_rule["mandatory_ports"]
        o_ports = fusion_rule["optional_ports"]
        o_ports_threshhold = fusion_rule["optional_ports_threshold"]
        correlation = fusion_rule["correlation"]
        self.set_fusion_rule(m_ports, o_ports,
                             o_ports_threshhold, correlation)

    def set_fusion_rule(self, m_ports, o_ports, o_ports_threshhold, correlation):
        self._fusion_rule = self.FusionRule(
            m_ports, o_ports, o_ports_threshhold, correlation)

    def _check_and_fusion(self, msg, topic_name):
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
