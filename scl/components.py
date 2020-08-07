from rclpy.node import Node
from .channel import InputPort, OutputPort
from .clink import Event, Mode


class Component(Node):
    def __init__(self, name):
        self.__name = name
        self.__input_ports = []
        self.__output_ports = []
        self.__events = []
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
                self.__input_ports.append(
                    InputPort(self, msg_type, topic_name, callback))
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
                self.__output_ports.append(
                    OutputPort(self, msg_type, topic_name))

    def register_event_callback(self, srv, event, callback):
        self.__events.append(Event(self, srv, event, callback))

    def setup(self):
        pass

    def run(self):
        pass


class ProcessingComponent(Component):
    def __init__(self):
        pass


class SourceComponent(Component):
    def __init__(self):
        pass


class SinkComponent(Component):
    def __init__(self):
        pass


class FusionOperator(Component):
    def __init__(self):
        pass
