import rclpy
from .executor import SplashExecutor
from srl.mode_change import ModeManager

class BuildUnit:
    def __init__(self, name):
        self.name = name
        self.context = rclpy.init()
        self._components = {}
        self._executor = SplashExecutor()
        self._mode_manager = ModeManager(self.context)
        self._mode_manager.set_handler(self._modechange_handler)
    
    def add(self, component):
        self._components[component.name] = component

    def run(self):        
        self._executor.add_node(self._mode_manager)
        for component in self._components.values():
            self._executor.add_node(component)
        
        try:
            while rclpy.ok():
                self._executor.spin_once()
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            for component in self._components.values():
                component.destroy_node()
            self._executor.shutdown()

    def configure_modechange(self, factory, modechange_configuration):
        self._mode_manager.set_modechange_configuration(factory, modechange_configuration)
    
    def _modechange_handler(self, factory, next_mode):
        print(next_mode)
        for mode in self._mode_manager.configuration_map[factory]['mode_list']:
            if mode["name"] == next_mode:
                for component in mode["components"]:
                    self._components[component].activate()
            else:
                for component in mode["components"]:
                    self._components[component].deactivate()

    