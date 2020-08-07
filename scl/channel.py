from rclpy.qos import QoSProfile


class InputPort():
    def __init__(self, component, msg_type, channel, callback):
        self.__component = component
        self.__msg_type = msg_type
        self.__channel = channel
        self.__callback = callback
        self.__subscription = self.__component.create_subscription(
            self.__msg_type, self.__channel, self.__callback, 1)


class OutputPort():
    def __init__(self, component, msg_type, channel):
        self.__component = component
        self.__msg_type = msg_type
        self.__channel = channel
        self.__publisher = self.__component.create_publisher(
            self.__msg_type, self.__channel, 1)

    def write(self, msg):
        self.__publisher.publish(msg)
