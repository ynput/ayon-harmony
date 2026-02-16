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


class TemplateLoaderPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    override_name: str = SettingsField(
        "",
        title="Override container name",
        description=(
            "Optional container name to override the default name.\n"
            "Keys are available in the context of the loader plugin.\n"
            "Example keys: project[name], folder[name], product[name]..."
        ),
        placeholder="{folder[name]}_{product[name]}",
    )


class HarmonyLoadPlugins(BaseSettingsModel):
    ImageLoader: ImageLoaderPluginModel = SettingsField(
        title="ImageLoader",
        default_factory=ImageLoaderPluginModel,
    )

    TemplateLoader: TemplateLoaderPluginModel = SettingsField(
        default_factory=TemplateLoaderPluginModel,
        title="Template Loader",
    )
