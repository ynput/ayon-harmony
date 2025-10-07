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


def compression_enum():
    return [
        {"value": "ZIP", "label": "ZIP"},
        {"value": "ZIPS", "label": "ZIPS"},
        {"value": "DWAA", "label": "DWAA"},
        {"value": "DWAB", "label": "DWAB"},
        {"value": "PIZ", "label": "PIZ"},
        {"value": "RLE", "label": "RLE"},
        {"value": "PXR24", "label": "PXR24"},
        {"value": "B44", "label": "B44"},
        {"value": "B44A", "label": "B44A"},
        {"value": "none", "label": "None"}
    ]


def user_exr_choices():
    return [
        {"value": "create_exr", "label": "Create EXR"},
        {"value": "multichannel_exr", "label": "Create multichannel EXR"},
        {"value": "keep_passes", "label": "Keep render passes"},
    ]


class ExtractConvertToEXRModel(BaseSettingsModel):
    """WARNING: This plugin does not work on MacOS (using OIIO tool)."""
    enabled: bool = False
    replace_pngs: bool = SettingsField(
        True,
        title="Replace original PNG files",
        description="Remove original PNG files after transcoding to EXR",
    )
    auto_trim: bool = SettingsField(
        True,
        title="Auto Trim",
    )
    exr_compression: str = SettingsField(
        "ZIP",
        enum_resolver=compression_enum,
        title="EXR Compression"
    )
    multichannel_exr: bool = SettingsField(
        False,
        title="Create multichannel EXR",
        description="Merge render passes into a render layer EXR files",
    )
    keep_passes: bool = SettingsField(
        False,
        title="Keep render passes",
        description=(
            "Keep render passes even though multichannel EXR is enabled"
        ),
    )
    user_overrides: list[str] = SettingsField(
        default_factory=list,
        title="User overrides",
        description="Allow user to change the plugin functionality",
        enum_resolver=user_exr_choices,
    )


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

    ExtractConvertToEXR: ExtractConvertToEXRModel = SettingsField(
        default_factory=ExtractConvertToEXRModel,
        title="Extract Convert To EXR"
    )
