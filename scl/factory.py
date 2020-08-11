from .impl.singleton import Singleton


class Factory(Singleton):
    def __init__(self, name, parent, mode_configuration):
        self.name = name
        self.parent = parent
        self.mode_configuration = mode_configuration
