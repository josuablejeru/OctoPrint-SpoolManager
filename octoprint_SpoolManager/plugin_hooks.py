from .spool_manager_plugin import SpoolmanagerPlugin
from .filament_odometer import FilamentOdometer
from octoprint_SpoolManager.common.EventBusKeys import EventBusKeys

class PluginHooks:
    """ handles plugin hooks """

    def __init__(self, plugin: SpoolmanagerPlugin, filament_odometer: FilamentOdometer) -> None:
        self.plugin = plugin
        self.filament_odometer = filament_odometer


    def get_update_information(self):
        """
        Software update hook
        """
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        update_information = dict(
            SpoolManager=dict(
                displayName="SpoolManager Plugin",
                displayVersion=self.plugin._plugin_version,
                # version check: github repository
                type="github_release",
                user="OllisGit",
                repo="OctoPrint-SpoolManager",
                current=self.plugin._plugin_version,
                # Release channels
                stable_branch=dict(
                    name="Only Release", branch="master", comittish=["master"]
                ),
                prerelease_branches=[
                    dict(
                        name="Release & Candidate",
                        branch="pre-release",
                        comittish=["pre-release", "master"],
                    ),
                    dict(
                        name="Release & Candidate & under Development",
                        branch="development",
                        comittish=["development", "pre-release", "master"],
                    ),
                ],
                # update method: pip
                pip="https://github.com/josuablejeru/OctoPrint-SpoolManager/releases/download/{target_version}/master.zip",
            )
        )

        return update_information


    def on_sentGCodeHook(
        self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs
    ):
        """
        Listen to all g-code which where already sent to the printer
        (thread: comm.sending_thread)
        """

        self.filament_odometer.processGCodeLine(cmd)

    def register_custom_events(*args, **kwargs):
        return [
            EventBusKeys.EVENT_BUS_SPOOL_WEIGHT_UPDATED_AFTER_PRINT,
            EventBusKeys.EVENT_BUS_SPOOL_SELECTED,
            EventBusKeys.EVENT_BUS_SPOOL_DESELECTED,
            EventBusKeys.EVENT_BUS_SPOOL_ADDED,
            EventBusKeys.EVENT_BUS_SPOOL_DELETED,
        ]
