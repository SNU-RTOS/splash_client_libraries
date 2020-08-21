from srl.rate_controller import RateController

class StreamPort():
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self._namespace = None

    def get_channel(self):
        return self._channel
        
    def set_channel(self, channel):
        self._channel = channel

    def set_msg_type(self, msg_type):
        self._msg_type = msg_type

    def set_namespace(self, namespace):
        self._namespace = namespace

    def get_namespace(self):
        return self._namespace

class StreamInputPort(StreamPort):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self._data_queue = []

    def attach(self):
        topic = self._namespace + "/" + self._channel if self._namespace else self._channel
        self._subscription = self.parent.create_subscription(
            self._msg_type, topic, self._check_mode_and_execute_callback, 1)

    def set_callback(self, callback, args=None):
        self._callback = callback
        self._args = args
    
    def set_freshness_constraint(self, freshness_constraint):
        self.freshness_constraint = freshness_constraint

    def _check_mode_and_execute_callback(self, msg):
        if self.parent.mode == self.parent.get_current_mode():
            if self._args:
                self._callback(msg, self._args[0])
            else:
                self._callback(msg)
        else:
            pass

class StreamOutputPort(StreamPort):
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self._rate_constraint = 0
    def attach(self):
        self._topic = self._namespace + "/" + self._channel if self._namespace else self._channel
        self._publisher = self.parent.create_publisher(
            self._msg_type, self._topic, 10)
        if self._rate_constraint > 0:
            self._rate_controller = RateController(self)

    def set_rate_constraint(self, rate_constraint):
        self._rate_constraint = rate_constraint

    def get_rate_constraint(self):
        return self._rate_constraint

    def write(self, msg):
        if self._rate_constraint > 0:
            self._rate_controller.push(msg)
        else:
            self._publisher.publish(msg)

    def get_publisher(self):
        return self._publisher