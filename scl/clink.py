from rclpy.service import Service


class ModeChangeOutputPort:
    def __init__(self, component, mode):
        self.__component = component
        self.__mode = mode


class EventInputPort:
    def __init__(self, component, srv, event, callback):
        self.__component = component
        self.__event = event
        self.__callback = callback
        self.__service = self.__component.create_service(srv, event, callback)


class EventOutputPort:
    def __init__(self, component, srv, event):
        self.__component = component
        self.__event = event
        self.__client = self.__component.create_client(srv, event)
