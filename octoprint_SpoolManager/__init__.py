from .spool_manager_plugin import SpoolmanagerPlugin
from .plugin_hooks import PluginHooks
from .filament_odometer import FilamentOdometer

__plugin_name__ = "SpoolManager Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    filament_odometer = FilamentOdometer()

    global __plugin_implementation__
    __plugin_implementation__ = SpoolmanagerPlugin(filament_odometer)

    hooks = PluginHooks(plugin=__plugin_implementation__, filament_odometer=filament_odometer)

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": hooks.get_update_information,
        "octoprint.comm.protocol.gcode.sent": hooks.on_sentGCodeHook,
        "octoprint.events.register_custom_events": hooks.register_custom_events,
    }
