from ayon_server.settings import BaseSettingsModel, SettingsField


class ImageLoaderPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    expose_only_current_frame: bool = SettingsField(
        default=False,
        title="Expose only current frame",
        description=(
          "If enabled, only the current frame will be exposed, "
          "all other frames will be set to empty.",
        ),
    )


class BackdropLoaderPluginModel(BaseSettingsModel):
    """Shared model for backdrop-based loaders."""

    enabled: bool = SettingsField(True, title="Enabled")


class HarmonyLoadPlugins(BaseSettingsModel):
    """Harmony loader plugins settings."""

    override_name: str = SettingsField(
        "",
        title="Override container name",
        description=(
            "Optional container name to override the default name for "
            "backdrop loaders (templates, PSD layers).\n"
            "Keys are available in the context of the loader plugin.\n"
            "Example keys: project[name], folder[name], product[name]...\n"
            "Example value: {folder[name]}-{product[name]}"
        ),
    )


class HarmonyLoadPlugins(BaseSettingsModel):
    ImageLoader: ImageLoaderPluginModel = SettingsField(
        title="ImageLoader",
        default_factory=ImageLoaderPluginModel,
    )
    TemplateLoader: BackdropLoaderPluginModel = SettingsField(
        default_factory=BackdropLoaderPluginModel,
        title="Template Loader",
    )
    PsdLoader: BackdropLoaderPluginModel = SettingsField(
        default_factory=BackdropLoaderPluginModel,
        title="Load Photoshop Layers",
    )
