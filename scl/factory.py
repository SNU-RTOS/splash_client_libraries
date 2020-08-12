from .impl.singleton import Singleton


class Factory(Singleton):
    def __init__(self, name, parent, mode_configuration, mode):
        self.name = name
        self.parent = parent
        self.mode_configuration = mode_configuration
        self.mode = mode

    def get_namespace(self):
        parent = self.parent
        name = self.name
        name = self.mode + "/" + name if self.mode else name
        if(parent):
            name = parent.get_namespace() + "/" + name
        return name
