from rclpy.node import Node
from rclpy.time import Time
from .ports import StreamInputPort, StreamOutputPort, EventInputPort, EventOutputPort, ModeChangePort
from std_msgs.msg import String, Header
from splash_interfaces.msg import SplashMessage
from typing import Callable
from array import *

import inspect
import pickle
import time
class Component(Node):
    def __init__(self, name):
        super().__init__(name)
        self.name = name
        self.stream_input_ports = {}
        self.stream_output_ports = {}
        self.event_input_ports = {}
        self.event_output_ports = {}
        self.mode_change_ports = {}
        self.callbacks = {}
        self.freshness = 0

class ProcessingComponent(Component):
    def __init__(self, name):
        super().__init__(name)
        
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
        event: str
    ):
        self.mode_change_ports[factory] = ModeChangePort(self, name, factory, event)

    def write(self, channel, msg):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        caller_name = calframe[1][3]
        source_msg = None

        port = self.stream_output_ports[channel]

        if caller_name == port.callback.__name__:
            source_msg = port.msg_list[0]

        splash_msg = SplashMessage()

        if source_msg:
            splash_msg.header = source_msg.header
            splash_msg.freshness = source_msg.freshness
        else:
            header = Header()
            header.stamp = self.get_clock().now().to_msg()
            header.frame_id = self.name
            splash_msg.header = header
            splash_msg.freshness = self.freshness

        serialized_data = array('B', pickle.dumps(msg))
        splash_msg.body = serialized_data

        port.write(splash_msg)

    def trigger_event(self, event):
        self.event_output_ports[event].trigger()

    def trigger_modechange(self, factory, event):
        self.mode_change_ports[factory].trigger(event)
    
class SourceComponent(Component):
    def __init__(self, name):
        super().__init__(name)

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
        splash_msg.freshness = self.freshness
        port.write(splash_msg)

class SinkComponent(Component):
    def __init__(self, name):
        super().__init__(name)

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
    class FusionedObj(object):
        def __init__(self, d):
            for key, value in d.items():
                if isinstance(value, (list, tuple)):
                    setattr(self, key, [FusionOperator.FusionedObj(x) if isinstance(x, dict) else x for x in value])
                else:
                    setattr(self, key, FusionOperator.FusionedObj(value) if isinstance(value, dict) else value)
    class FusionRule():
        def __init__(self, mandatory_ports, optional_ports, optional_ports_threshold, correlation_constraint):
            self.mandatory_ports = mandatory_ports
            self.optional_ports = optional_ports
            self.optional_ports_threshold = optional_ports_threshold
            self.correlation_constraint = correlation_constraint

    def __init__(self, name):
        super().__init__(name)
        self.fusion_rule = None
        self.queues_for_input_ports = {}

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

        for channel in mandatory_ports:
            mandatory_port_objs.append(self.stream_input_ports[channel])
        for channel in optional_ports:
            optional_port_objs.append(self.stream_input_ports[channel])
        
        self.fusion_rule = FusionOperator.FusionRule(mandatory_port_objs, optional_port_objs, optional_ports_threshold, correlation_constraint)
        for channel in self.stream_input_ports.keys():
            self.queues_for_input_ports[channel] = []

    def _fusion_callback(self, channel, msg):
        # deserialized_data = pickle.loads(msg.body)
        # self.callbacks[channel](self, deserialized_data)
        self.queues_for_input_ports[channel].append(msg)
        # print(channel, len(self.queues_for_input_ports[channel]))
        valid_input_data = self._find_valid_input_data()
        oldest_birthmark = None
        if valid_input_data:
            for c, data in valid_input_data.items():
                if oldest_birthmark == None or Time.from_msg(data.header.stamp) < Time.from_msg(oldest_birthmark):
                    oldest_birthmark = data.header.stamp
                    freshness = data.freshness
                valid_input_data[c] = pickle.loads(data.body)
            splash_message = SplashMessage()
            header = Header()
            header.stamp = oldest_birthmark
            splash_message.header = header
            splash_message.body = array('B', pickle.dumps(valid_input_data))
            splash_message.freshness = freshness
            self.stream_output_ports[self.output_channel].write(splash_message)
        else:
            pass
    def _find_valid_input_data(self):
        # print('find valid input data')
        index_list = [None] * len(self.queues_for_input_ports.keys())
        i = 0
        optional_ports_count = 0

        for mandatory_port in self.fusion_rule.mandatory_ports:
            queue = next((item for key, item in self.queues_for_input_ports.items() if mandatory_port.channel == key), False)
            if not queue or len(queue) == 0:
                return None
        
        for channel, queue in self.queues_for_input_ports.items():
            if len(queue) > 0:
                index_list[i] = 0
                if next((item for item in self.fusion_rule.optional_ports if item.channel == channel), False):
                    optional_ports_count = optional_ports_count + 1
            i = i + 1
        
        if optional_ports_count < self.fusion_rule.optional_ports_threshold:
            return None
        
        flag = True
        while flag:
            if self._is_valid_data(index_list):
                return self._build_data(index_list)
            k, is_last = self._get_earlist_index(index_list)

            if is_last:
                index_list[k] = None
            else:
                index_list[k] = index_list[k] + 1
            flag = False
            for index in index_list:
                if index is not None:
                    flag = True
                    break
        return None

    def _is_valid_data(self, index_list):
        # print('check is valid data')
        i = 0
        cur_data_list = []
        for queue in self.queues_for_input_ports.values():
            if index_list[i] is not None:
                cur_data_list.append(queue[index_list[i]])
            i = i + 1
        if len(cur_data_list) < 2:
            return False
        
        for data in cur_data_list:
            for data2 in cur_data_list:
                if data == data2: continue
                time_diff_ms = abs(Time.from_msg(data.header.stamp).nanoseconds - Time.from_msg(data2.header.stamp).nanoseconds) / 1000000
                if time_diff_ms > self.fusion_rule.correlation_constraint:
                    return False
            return True
    
    def _build_data(self, index_list):
        # print('build data')

        i = 0
        data = {}
        for key, queue in self.queues_for_input_ports.items():
            data[key] = None
            if index_list[i] is not None:
                data[key] = queue[index_list[i]]
                if len(queue) == index_list[i] + 1:
                    queue = []
                else:
                    queue = queue[index_list[i]+1:]
                self.queues_for_input_ports[key] = queue
            i = i + 1

        return data
    
    def _get_earlist_index(self, index_list):
        # print('get earlist index')

        is_last = False
        earlist_index = -1
        index = 0
        queue_list = []
        for queue in self.queues_for_input_ports.values():
            queue_list.append(queue)
            index = index + 1
        index = 0
        for queue in queue_list:
            if index_list[index] is not None:
                if earlist_index < 0 or (len(queue) > 0 and Time.from_msg(queue[index_list[index]].header.stamp) < Time.from_msg(queue_list[earlist_index][index_list[earlist_index]].header.stamp)):
                    earlist_index = index
                index = index + 1
            if len(queue_list[earlist_index]) == index_list[earlist_index] + 1:
                is_last = True

            return earlist_index, is_last

