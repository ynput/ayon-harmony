from ayon_server.settings import BaseSettingsModel, SettingsField


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
    TemplateLoader: TemplateLoaderPluginModel = SettingsField(
        default_factory=TemplateLoaderPluginModel,
        title="Template Loader",
    )
