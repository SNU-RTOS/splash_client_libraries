from rclpy.qos import QoSProfile


class StreamInputPort():
    def __init__(self, component, msg_type, channel, callback):
        self.__component = component
        self.__msg_type = msg_type
        self.__channel = channel
        self.__callback = callback
        self.__subscription = self.__component.create_subscription(
            self.__msg_type, self.__channel, self.__callback, 1)
        self.__data_queue = []

    def set_freshness_constraint(self, freshness_constraint):
        self.freshness_constraint = freshness_constraint

    def get_type(self):
        return self.__msg_type


class StreamOutputPort():
    def __init__(self, component, msg_type, channel):
        self.__component = component
        self.__msg_type = msg_type
        self.__channel = channel
        self.__publisher = self.__component.create_publisher(
            self.__msg_type, self.__channel, 1)

    def set_rate_constraint(self, rate_constraint):
        self.rate_constraint = rate_constraint

    def get_type(self):
        return self.__msg_type

    def write(self, msg):
        self.__publisher.publish(msg)
