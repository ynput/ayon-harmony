from ayon_server.settings import BaseSettingsModel, SettingsField


class CollectPalettesPlugin(BaseSettingsModel):
    """Set regular expressions to filter triggering on specific task names. '.*' means on all."""  # noqa

    allowed_tasks: list[str] = SettingsField(
        default_factory=list,
        title="Allowed tasks"
    )


class ValidateAudioPlugin(BaseSettingsModel):
    """Check if scene contains audio track."""  #
    _isGroup = True
    enabled: bool = True
    optional: bool = SettingsField(True, title="Optional")
    active: bool = SettingsField(True, title="Active")


class ValidateSceneSettingsPlugin(BaseSettingsModel):
    """Validate if FrameStart, FrameEnd and Resolution match shot data in DB.
       Use regular expressions to limit validations only on particular folder
       or task names."""
    _isGroup = True
    enabled: bool = True
    optional: bool = SettingsField(False, title="Optional")
    active: bool = SettingsField(True, title="Active")

    frame_check_filter: list[str] = SettingsField(
        default_factory=list,
        title="Skip Frame check for Folder Paths with name containing"
    )

    skip_resolution_check: list[str] = SettingsField(
        default_factory=list,
        title="Skip Resolution Check for Tasks"
    )

    skip_timelines_check: list[str] = SettingsField(
        default_factory=list,
        title="Skip Timeline Check for Tasks"
    )


class ValidateInstancePlugin(BaseSettingsModel):
    """Validate if instance folder is the current folder."""
    enabled: bool = True
    optional: bool = SettingsField(False, title="Optional")
    active: bool = SettingsField(True, title="Active")


class HarmonyPublishPlugins(BaseSettingsModel):

    CollectPalettes: CollectPalettesPlugin = SettingsField(
        title="Collect Palettes",
        default_factory=CollectPalettesPlugin,
    )

    ValidateAudio: ValidateAudioPlugin = SettingsField(
        title="Validate Audio",
        default_factory=ValidateAudioPlugin,
    )

    ValidateSceneSettings: ValidateSceneSettingsPlugin = SettingsField(
        title="Validate Scene Settings",
        default_factory=ValidateSceneSettingsPlugin,
    )

    ValidateInstance: ValidateInstancePlugin = SettingsField(
        title="Validate Instance",
        default_factory=ValidateInstancePlugin,
    )
