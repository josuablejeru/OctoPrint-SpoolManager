from .spool_manager_plugin import SpoolmanagerPlugin

__plugin_name__ = "SpoolManager Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SpoolmanagerPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.on_sentGCodeHook,
        # "octoprint.comm.protocol.scripts": __plugin_implementation__.message_on_connect
        "octoprint.events.register_custom_events": __plugin_implementation__.register_custom_events,
    }
