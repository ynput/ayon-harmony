from ayon_server.settings import BaseSettingsModel, SettingsField


class ImageLoaderPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    expose_only_current_frame: bool = SettingsField(
        False,
        title="Expose only current frame",
        description="If enabled, only the current frame will be exposed, "
        "all other frames will be set to empty.",
    )


class HarmonyLoadPlugins(BaseSettingsModel):
    ImageLoader: ImageLoaderPluginModel = SettingsField(
        title="ImageLoader",
        default_factory=ImageLoaderPluginModel,
    )
