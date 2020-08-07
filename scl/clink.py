from rclpy.service import Service


class Mode:
    def __init__(self):
        pass


class Event:
    def __init__(self, component, srv, event, callback):
        self.__component = component
        self.__event = event
        self.__callback = callback
        self.__service = self.__component.create_service(srv, event, callback)
